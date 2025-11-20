/*
 * Copyright (c) 2024 Your Name
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none

module tt_um_example (
    input  wire [7:0] ui_in,    // Dedicated inputs
    output wire [7:0] uo_out,   // Dedicated outputs
    input  wire [7:0] uio_in,   // IOs: Input path
    output wire [7:0] uio_out,  // IOs: Output path
    output wire [7:0] uio_oe,   // IOs: Enable path (active high: 0=input, 1=output)
    input  wire       ena,      // always 1 when the design is powered, so you can ignore it
    input  wire       clk,      // clock
    input  wire       rst_n     // reset_n - low to reset
);
  //sets reg
  reg [7:0] counter;

  wire load = uio_in[0];
  wire [7:0]dat = ui_in;

  // All output pins must be assigned. If not used, assign to 0.
  //assign uo_out  = ui_in + uio_in;  // Example: ou_out is the sum of ui_in and uio_in
  always @(posedge clk or negedge rst_n) begin
    if (!rst_n)
      counter <= 8'd0;
    else if (load && ena)
      counter <= dat;
    else if (ena)
      counter <= counter + 8'b1;
  end

  assign uo_out  = ena ? counter : 8'bZ;
  assign uio_out = 8'bZ;
  assign uio_oe  = 8'bZ;

  // List all unused inputs to prevent warnings
    wire _unused = &{ena, clk, rst_n, uio_in, 1'b0};

endmodule
