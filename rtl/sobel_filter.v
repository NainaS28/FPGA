// ============================================================================
// sobel_filter.v
// 3x3 Sobel gradient magnitude, pipelined in 2 stages
// (latency = 2 clocks, throughput = 1 window per clock).
//
//        Gx kernel          Gy kernel          window
//      -1  0 +1           -1 -2 -1          w0 w1 w2
//      -2  0 +2            0  0  0          w3 w4 w5
//      -1  0 +1           +1 +2 +1          w6 w7 w8
//
//   Stage 1: Gx = (w2 + 2*w5 + w8) - (w0 + 2*w3 + w6)
//            Gy = (w6 + 2*w7 + w8) - (w0 + 2*w1 + w2)
//            (multiply by 2 is a 1-bit left shift: no multipliers needed)
//   Stage 2: magnitude = |Gx| + |Gy|      (11 bits; largest possible value is
//            1530, e.g. Gx = 1020 and Gy = 510)
//
// Same integer arithmetic as python/dip.py: sobel_mag().
// ============================================================================
module sobel_filter (
    input  wire        clk,
    input  wire        rst,
    input  wire [7:0]  w0, w1, w2, w3, w4, w5, w6, w7, w8,
    input  wire        valid_in,
    output reg  [10:0] mag,
    output reg         valid_out
);
    // Each weighted column/row sum is at most 4*255 = 1020 -> 10 bits unsigned
    wire [9:0] gx_pos = {2'b00, w2} + {1'b0, w5, 1'b0} + {2'b00, w8};
    wire [9:0] gx_neg = {2'b00, w0} + {1'b0, w3, 1'b0} + {2'b00, w6};
    wire [9:0] gy_pos = {2'b00, w6} + {1'b0, w7, 1'b0} + {2'b00, w8};
    wire [9:0] gy_neg = {2'b00, w0} + {1'b0, w1, 1'b0} + {2'b00, w2};

    // ---- Stage 1: signed gradients (-1020 .. +1020 -> 11-bit signed) ----
    reg signed [10:0] gx, gy;
    reg               v1;

    // ---- Stage 2: absolute values and sum ----
    wire [9:0] abs_gx = gx[10] ? -gx[9:0] : gx[9:0];
    wire [9:0] abs_gy = gy[10] ? -gy[9:0] : gy[9:0];

    always @(posedge clk) begin
        if (rst) begin
            v1 <= 1'b0; valid_out <= 1'b0;
        end else begin
            gx <= $signed({1'b0, gx_pos}) - $signed({1'b0, gx_neg});
            gy <= $signed({1'b0, gy_pos}) - $signed({1'b0, gy_neg});
            v1 <= valid_in;

            mag       <= {1'b0, abs_gx} + {1'b0, abs_gy};
            valid_out <= v1;
        end
    end
endmodule
