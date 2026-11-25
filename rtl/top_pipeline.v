// ============================================================================
// top_pipeline.v
// Phase 2 top level: the complete streaming image-processing pipeline.
//
//   pixel -> window_buffer -> median_filter -> window_buffer -> sobel_filter
//         -> threshold -> edge bit
//
// Input : one 8-bit pixel per clock (when valid_in = 1), raster order,
//         WIDTH x HEIGHT image.
// Output: denoised pixels, (WIDTH-2) x (HEIGHT-2)        (median_out)
//         edge bits,       (WIDTH-4) x (HEIGHT-4)        (edge_out)
// Latency through each block (register stages):
//   window 1 + median 3 + window 1 + Sobel 2 + threshold 1 = 8 stages
// Throughput: 1 pixel per clock. Input pauses (valid_in = 0) are allowed.
// ============================================================================
module top_pipeline #(
    parameter WIDTH  = 128,
    parameter HEIGHT = 128
)(
    input  wire        clk,
    input  wire        rst,
    input  wire [7:0]  pix_in,
    input  wire        valid_in,
    input  wire [10:0] thr,          // edge threshold (default 200)
    output wire [7:0]  median_out,
    output wire        median_valid,
    output wire [10:0] mag_out,
    output wire        mag_valid,
    output wire        edge_out,
    output wire        edge_valid
);
    // ---- Stage A: denoise ----
    median_stream #(.WIDTH(WIDTH), .HEIGHT(HEIGHT)) u_med (
        .clk(clk), .rst(rst), .pix_in(pix_in), .valid_in(valid_in),
        .median_out(median_out), .median_valid(median_valid));

    // ---- Stage B: 3x3 window on the denoised (WIDTH-2)x(HEIGHT-2) image ----
    wire [7:0] s0, s1, s2, s3, s4, s5, s6, s7, s8;
    wire       swin_valid;
    window_buffer #(.WIDTH(WIDTH-2), .HEIGHT(HEIGHT-2)) u_win2 (
        .clk(clk), .rst(rst), .pix_in(median_out), .valid_in(median_valid),
        .w0(s0), .w1(s1), .w2(s2), .w3(s3), .w4(s4), .w5(s5), .w6(s6), .w7(s7), .w8(s8),
        .valid_out(swin_valid));

    // ---- Stage C: Sobel magnitude ----
    sobel_filter u_sobel (
        .clk(clk), .rst(rst),
        .w0(s0), .w1(s1), .w2(s2), .w3(s3), .w4(s4), .w5(s5), .w6(s6), .w7(s7), .w8(s8),
        .valid_in(swin_valid), .mag(mag_out), .valid_out(mag_valid));

    // ---- Stage D: threshold -> edge bit ----
    threshold u_thr (
        .clk(clk), .rst(rst), .mag(mag_out), .thr(thr), .valid_in(mag_valid),
        .edge_out(edge_out), .valid_out(edge_valid));
endmodule
