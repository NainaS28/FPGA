// ============================================================================
// median_filter.v
// 3x3 median filter, pipelined in 3 stages (latency = 3 clocks,
// throughput = 1 window per clock).
//
// Instead of fully sorting 9 values, it uses a well-known shortcut that gives
// the EXACT same median with far fewer comparators:
//   Stage 1: sort each row of 3            -> (lo, mid, hi) per row
//   Stage 2: A = max of the three lo's
//            B = median of the three mid's
//            C = min of the three hi's
//   Stage 3: median = median(A, B, C)
// (python/dip.py: median3x3_hw_style() proves this equals the true median.)
// ============================================================================
module median_filter (
    input  wire       clk,
    input  wire       rst,
    input  wire [7:0] w0, w1, w2, w3, w4, w5, w6, w7, w8,
    input  wire       valid_in,
    output reg  [7:0] median,
    output reg        valid_out
);
    // ---- small helper functions (become comparators + multiplexers) ----
    function [7:0] min2(input [7:0] a, input [7:0] b); min2 = (a < b) ? a : b; endfunction
    function [7:0] max2(input [7:0] a, input [7:0] b); max2 = (a > b) ? a : b; endfunction
    function [7:0] min3(input [7:0] a, input [7:0] b, input [7:0] c); min3 = min2(a, min2(b, c)); endfunction
    function [7:0] max3(input [7:0] a, input [7:0] b, input [7:0] c); max3 = max2(a, max2(b, c)); endfunction
    // median of 3 = max(min(a,b), min(max(a,b), c))
    function [7:0] med3(input [7:0] a, input [7:0] b, input [7:0] c);
        med3 = max2(min2(a, b), min2(max2(a, b), c));
    endfunction

    // ---- Stage 1: sort each row ----
    reg [7:0] lo0, mi0, hi0, lo1, mi1, hi1, lo2, mi2, hi2;
    reg       v1;
    // ---- Stage 2: combine columns ----
    reg [7:0] A, B, C;
    reg       v2;

    always @(posedge clk) begin
        if (rst) begin
            v1 <= 1'b0; v2 <= 1'b0; valid_out <= 1'b0;
        end else begin
            // Stage 1
            lo0 <= min3(w0, w1, w2); mi0 <= med3(w0, w1, w2); hi0 <= max3(w0, w1, w2);
            lo1 <= min3(w3, w4, w5); mi1 <= med3(w3, w4, w5); hi1 <= max3(w3, w4, w5);
            lo2 <= min3(w6, w7, w8); mi2 <= med3(w6, w7, w8); hi2 <= max3(w6, w7, w8);
            v1  <= valid_in;
            // Stage 2
            A  <= max3(lo0, lo1, lo2);
            B  <= med3(mi0, mi1, mi2);
            C  <= min3(hi0, hi1, hi2);
            v2 <= v1;
            // Stage 3
            median    <= med3(A, B, C);
            valid_out <= v2;
        end
    end
endmodule
