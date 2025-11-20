import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer


# Opcodes (ui_in[2:0])
OP_ADD = 0b000
OP_OR  = 0b001
OP_AND = 0b010
OP_NOR = 0b011
OP_SHL = 0b100
OP_SHR = 0b101
OP_SUB = 0b110


async def reset_dut(dut):
    """Reset helper: drive rst_n low, then high."""
    dut.rst_n.value = 0
    dut.ena.value   = 0
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    await Timer(20, units="ns")
    dut.rst_n.value = 1
    dut.ena.value   = 1
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)


async def apply_and_check(dut, opcode, A, B, exp_y, exp_flag, desc=""):
    """
    Apply one operation and check result.

    NOTE: func_sel is ui_in[2:0], so A's low 3 bits must equal opcode.
    This test chooses A that already satisfies that.
    """
    assert (A & 0b111) == opcode, f"A={A:#04x} does not encode opcode {opcode:03b}"

    dut.ui_in.value  = A
    dut.uio_in.value = B

    await RisingEdge(dut.clk)   # inputs sampled
    await RisingEdge(dut.clk)   # outputs registered

    got_y    = int(dut.uo_out.value)
    got_flag = int(dut.uio_out.value & 0x1)  # bit 0

    msg = f"{desc} (opcode={opcode:03b}, A=0x{A:02X}, B=0x{B:02X})"

    assert got_y == (exp_y & 0xFF), (
        f"Result mismatch: {msg}: got 0x{got_y:02X}, expected 0x{exp_y & 0xFF:02X}"
    )
    assert got_flag == (exp_flag & 0x1), (
        f"Flag mismatch: {msg}: got {got_flag}, expected {exp_flag & 0x1}"
    )


@cocotb.test()
async def test_basic_ops(dut):
    """Sanity-check all ALU operations: ADD, SUB, OR, AND, NOR, SHL, SHR."""

    # Create and start a 10 ns period clock on dut.clk
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())

    # Reset
    await reset_dut(dut)

    # ---------------------- ADD tests (opcode 000) ---------------------------
    # Choose A with low 3 bits = 000
    A = 0b00101000  # 0x28
    B = 0x05
    exp = A + B
    exp_flag = 1 if exp > 0xFF else 0
    await apply_and_check(dut, OP_ADD, A, B, exp, exp_flag, "ADD 0x28 + 0x05")

    # ADD with carry out
    A = 0b11111000  # 0xF8 (low 3 bits 000)
    B = 0x20        # 32
    exp = A + B
    exp_flag = 1 if exp > 0xFF else 0
    await apply_and_check(dut, OP_ADD, A, B, exp, exp_flag, "ADD carry case")

    # ---------------------- SUB tests (opcode 110) ---------------------------
    # Choose A with low 3 bits = 110
    A = 0b00101110  # 0x2E
    B = 0x04
    tmp = (A - B) & 0x1FF
    exp = tmp & 0xFF
    exp_flag = (tmp >> 8) & 0x1  # borrow/flag from {flag, diff} = A - B
    await apply_and_check(dut, OP_SUB, A, B, exp, exp_flag, "SUB 0x2E - 0x04")

    # Underflow case
    A = 0b00000110  # 0x06 (low 3 bits 110)
    B = 0x20
    tmp = (A - B) & 0x1FF
    exp = tmp & 0xFF
    exp_flag = (tmp >> 8) & 0x1
    await apply_and_check(dut, OP_SUB, A, B, exp, exp_flag, "SUB underflow")

    # ---------------------- OR tests (opcode 001) ----------------------------
    A = 0b00101001  # 0x29, low 3 bits 001
    B = 0b00001111  # 0x0F
    exp = A | B
    await apply_and_check(dut, OP_OR, A, B, exp, 0, "OR")

    # ---------------------- AND tests (opcode 010) ---------------------------
    A = 0b01010110  # 0x56, low 3 bits 110 (oops) -> adjust to 010:
    A = (0x56 & 0xF8) | OP_AND  # force low 3 bits = 010
    B = 0b00111100  # 0x3C
    exp = A & B
    await apply_and_check(dut, OP_AND, A, B, exp, 0, "AND")

    # ---------------------- NOR tests (opcode 011) ---------------------------
    A = (0x5A & 0xF8) | OP_NOR  # force low 3 bits = 011
    B = 0x0F
    exp = (~(A | B)) & 0xFF
    await apply_and_check(dut, OP_NOR, A, B, exp, 0, "NOR")

    # ---------------------- SHL tests (opcode 100) ---------------------------
    # For shifts, B[2:0] is shift amount
    A = (0x11 & 0xF8) | OP_SHL  # low 3 bits = 100
    shamt = 2
    B = shamt  # upper bits ignored
    exp = (A << shamt) & 0xFF
    await apply_and_check(dut, OP_SHL, A, B, exp, 0, "SHIFT LEFT by 2")

    # ---------------------- SHR tests (opcode 101) ---------------------------
    A = (0x88 & 0xF8) | OP_SHR  # low 3 bits = 101
    shamt = 3
    B = shamt
    exp = (A >> shamt) & 0xFF
    await apply_and_check(dut, OP_SHR, A, B, exp, 0, "SHIFT RIGHT by 3")
