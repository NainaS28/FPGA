// ============================================================================
// threshold.v
// Turns the Sobel magnitude into a 1-bit edge decision (1 clock of latency).
//     edge = 1  when  mag >= thr
// The threshold is an input, so it can be changed at run time
// (the project default is 200, the same as python/dip.py: THRESHOLD).
// ============================================================================
module threshold (
    input  wire        clk,
    input  wire        rst,
    input  wire [10:0] mag,
    input  wire [10:0] thr,
    input  wire        valid_in,
    output reg         edge_out,
    output reg         valid_out
);
    always @(posedge clk) begin
        if (rst) begin
            valid_out <= 1'b0;
            edge_out  <= 1'b0;
        end else begin
            edge_out  <= (mag >= thr);
            valid_out <= valid_in;
        end
    end
endmodule
