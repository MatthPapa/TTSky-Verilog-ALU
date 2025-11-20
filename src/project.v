`default_nettype none

// ---------------------------------------------------------------------------
// 8-bit adder: used for ADD operation
// ---------------------------------------------------------------------------
module adder8 (
    input  wire [7:0] a,
    input  wire [7:0] b,
    output wire [7:0] sum,
    output wire       cout
);
    assign {cout, sum} = a + b;
endmodule

// ---------------------------------------------------------------------------
// 8-bit logic unit: OR, AND, NOR
// sel encoding (matches func_sel[1:0] for opcodes 001,010,011):
//   2'b01 : OR
//   2'b10 : AND
//   2'b11 : NOR
//   2'b00 : (unused → 0)
// ---------------------------------------------------------------------------
module logic_unit8 (
    input  wire [7:0] a,
    input  wire [7:0] b,
    input  wire [1:0] sel,
    output reg  [7:0] y
);
    always @* begin
        case (sel)
            2'b01: y = a | b;         // OR
            2'b10: y = a & b;         // AND
            2'b11: y = ~(a | b);      // NOR
            default: y = 8'h00;       // unused / safe default
        endcase
    end
endmodule

// ---------------------------------------------------------------------------
// 8-bit logical shifter
// dir = 0 → shift left
// dir = 1 → shift right
// ---------------------------------------------------------------------------
module shifter8 (
    input  wire [7:0] a,
    input  wire [2:0] shamt,
    input  wire       dir,      // 0 = left, 1 = right
    output wire [7:0] y
);
    assign y = dir ? (a >> shamt) : (a << shamt);
endmodule

// ---------------------------------------------------------------------------
// Top-level ALU for TinyTapeout-style interface
//
//  Pins:
//    ui_in[7:0]  : A + function select in lower bits
//    uio_in[7:0] : B / shift amount (lower bits)
//    uo_out[7:0] : result (registered)
//    uio_out[0]  : flag/carry (registered), rest 0
//    uio_oe[0]   : 1 (drive flag), others 0
//
//  Function select (from ui_in[2:0]):
//    000 : ADD          (A + B)              [adder8]
//    001 : OR           (A | B)              [logic_unit8]
//    010 : AND          (A & B)              [logic_unit8]
//    011 : NOR          ~(A | B)             [logic_unit8]
//    100 : SHIFT LEFT   (A << shamt)         [shifter8, dir=0]
//    101 : SHIFT RIGHT  (A >> shamt)         [shifter8, dir=1]
//    110 : SUBTRACT     (A - B)              new
//    111 : reserved → 0
//
//  A     = ui_in[7:0]
//  B     = uio_in[7:0]
//  shamt = uio_in[2:0]
// ---------------------------------------------------------------------------
module tt_um_reg (
    input  wire [7:0] ui_in,
    output wire [7:0] uo_out,
    input  wire [7:0] uio_in,
    output wire [7:0] uio_out,
    output wire [7:0] uio_oe,
    input  wire       ena,
    input  wire       clk,
    input  wire       rst_n
);

    // Decode function select
    wire [2:0] func_sel = ui_in[2:0];

    wire [7:0] A = ui_in;
    wire [7:0] B = uio_in;
    wire [2:0] shamt = uio_in[2:0];

    // ---------------------- Submodule outputs -------------------------------
    // ADD
    wire [7:0] add_sum;
    wire       add_cout;

    adder8 u_adder8 (
        .a   (A),
        .b   (B),
        .sum (add_sum),
        .cout(add_cout)
    );

    // Logic (OR/AND/NOR)
    wire [7:0] logic_y;
    logic_unit8 u_logic8 (
        .a   (A),
        .b   (B),
        .sel (func_sel[1:0]),   // 00=OR, 01=AND, 10=NOR
        .y   (logic_y)
    );

    // Shifter
    wire [7:0] shift_y;
    wire       shift_dir = (func_sel == 3'b101) ? 1'b1 : 1'b0; // 100→left, 101→right

    shifter8 u_shifter8 (
        .a     (A),
        .shamt (shamt),
        .dir   (shift_dir),
        .y     (shift_y)
    );

    // SUBTRACT: A - B
    wire [7:0] sub_diff;
    wire       sub_flag;    // treat as borrow/flag bit
    assign {sub_flag, sub_diff} = A - B;

    // ---------------------- Operation select mux ----------------------------
    reg [7:0] alu_y;
    reg       alu_flag;  // use as carry/flag output

    always @* begin
        case (func_sel)
            3'b000: begin
                // ADD
                alu_y    = add_sum;
                alu_flag = add_cout;       // carry
            end

            3'b001,
            3'b010,
            3'b011: begin
                // logic ops: OR, AND, NOR
                alu_y    = logic_y;
                alu_flag = 1'b0;
            end

            3'b100: begin
                // shift left
                alu_y    = shift_y;
                alu_flag = 1'b0;
            end

            3'b101: begin
                // shift right
                alu_y    = shift_y;
                alu_flag = 1'b0;
            end

            3'b110: begin
                // SUBTRACT: A - B
                alu_y    = sub_diff;
                alu_flag = sub_flag;       // borrow/flag
            end

            default: begin
                alu_y    = 8'h00;
                alu_flag = 1'b0;
            end
        endcase
    end

    // ----------------------------- Registers --------------------------------
    reg [7:0] y_q;
    reg       flag_q;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            y_q    <= 8'h00;
            flag_q <= 1'b0;
        end else if (ena) begin
            y_q    <= alu_y;
            flag_q <= alu_flag;
        end
        // if ena == 0, hold previous values
    end

    // Outputs
    assign uo_out  = y_q;
    assign uio_out = {7'b0, flag_q};
    assign uio_oe  = 8'b0000_0001;   // only bit 0 drives

endmodule

`default_nettype wire
