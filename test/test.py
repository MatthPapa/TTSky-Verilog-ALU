# test/test.py
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ClockCycles


@cocotb.test()
async def test_reset_and_increment(dut):
    """After reset deasserts, counter should start at 0 and increment by 1 each cycle."""
    # Drive default values
    dut.ena.value    = 1
    dut.ui_in.value  = 0
    dut.uio_in.value = 0
    dut.clk.value    = 0
    dut.rst_n.value  = 0  # assert reset (active-low)

    # Start clock: 10 ns period (100 MHz)
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())

    # Hold reset for a couple of cycles
    await ClockCycles(dut.clk, 2)
    dut.rst_n.value = 1  # deassert reset

    await ClockCycles(dut.clk, 2)
    dut.rst_n.value = 0

    await RisingEdge(dut.clk)
    dut.rst_n.value = 1

    # After deasserting reset, first observed value should be 0 on the very next cycle
    await RisingEdge(dut.clk)
    val = int(dut.uo_out.value)
    assert val == 0, f"Counter after reset should be 0, got {val}"

    # Now check it increments by 1 each cycle for a few cycles
    prev = val
    for i in range(1, 10):
        await RisingEdge(dut.clk)
        val = int(dut.uo_out.value)
        expected = (prev + 1) & 0xFF
        assert val == expected, f"Cycle {i}: expected {expected}, got {val}"
        prev = val


@cocotb.test()
async def test_load_wraparound(dut):
    """Counter must wrap from 255 to 0."""
    # Re-init defaults
    dut.ena.value    = 0
    dut.ui_in.value  = 0
    dut.uio_in.value = 0
    dut.clk.value    = 0
    dut.rst_n.value  = 1

    # Start clock if not already running
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())

    await ClockCycles(dut.clk, 2);
    z_str = dut.uo_out.value.binstr  # e.g., 'ZZZZZZZZ'
    assert set(z_str.lower()) == {"z"}, f"Expected high Z, got {z_str}"
    dut.ena.value = 1

    # Hold reset for a couple of cycles
    await RisingEdge(dut.clk)
    dut.ui_in.value = 0xFE
    dut.uio_in.value = 1

    await RisingEdge(dut.clk)
    dut.uio_in.value = 0
    dut.ui_in.value = 0

    await RisingEdge(dut.clk)
    val_load = int(dut.uo_out.value)
    assert val_load == 0xFE, f"Expected 254, got {val_load}"

    # Next: 255
    await RisingEdge(dut.clk)
    val_255 = int(dut.uo_out.value)
    assert val_255 == 255, f"Expected 255, got {val_255}"

    # Wrap to 0
    await RisingEdge(dut.clk)
    val_0 = int(dut.uo_out.value)
    assert val_0 == 0, f"Expected wrap to 0, got {val_0}"

    # And then 1
    await RisingEdge(dut.clk)
    val_1 = int(dut.uo_out.value)
    assert val_1 == 1, f"Expected 1 after wrap, got {val_1}"
