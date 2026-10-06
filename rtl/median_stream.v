// ============================================================================
// median_stream.v
// Phase 1 top level: a streaming hardware denoiser.
//
//   pixel stream -> window_buffer -> median_filter -> denoised pixel stream
//
// Input : one 8-bit pixel per clock (when valid_in = 1), raster order,
//         WIDTH x HEIGHT image.
// Output: (WIDTH-2) x (HEIGHT-2) denoised pixels, one per clock.
// Latency: 4 clocks (1 window + 3 median stages).
//
// Phase 2 will add a second window_buffer, sobel_filter and threshold after
// this block to produce the edge map.
// ============================================================================
module median_stream #(
    parameter WIDTH  = 128,
    parameter HEIGHT = 128
)(
    input  wire       clk,
    input  wire       rst,
    input  wire [7:0] pix_in,
    input  wire       valid_in,
    output wire [7:0] median_out,
    output wire       median_valid
);
    // 3x3 window built from the incoming pixels
    wire [7:0] w0, w1, w2, w3, w4, w5, w6, w7, w8;
    wire       win_valid;

    window_buffer #(.WIDTH(WIDTH), .HEIGHT(HEIGHT)) u_win (
        .clk(clk), .rst(rst), .pix_in(pix_in), .valid_in(valid_in),
        .w0(w0), .w1(w1), .w2(w2), .w3(w3), .w4(w4), .w5(w5), .w6(w6), .w7(w7), .w8(w8),
        .valid_out(win_valid));

    // Median of each window
    median_filter u_median (
        .clk(clk), .rst(rst),
        .w0(w0), .w1(w1), .w2(w2), .w3(w3), .w4(w4), .w5(w5), .w6(w6), .w7(w7), .w8(w8),
        .valid_in(win_valid), .median(median_out), .valid_out(median_valid));
endmodule
