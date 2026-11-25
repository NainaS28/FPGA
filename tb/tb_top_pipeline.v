// ============================================================================
// tb_top_pipeline.v  -  End-to-end test of the complete Phase 2 hardware.
//
// 1. Streams the noisy 128x128 cameraman image into top_pipeline.
// 2. Checks every denoised pixel (126x126), every Sobel magnitude and every
//    edge bit (124x124) against the Python reference.
// 3. Writes the hardware outputs to results/rtl_median.hex and
//    results/rtl_edges.hex (python/compare_rtl.py rebuilds the images).
// 4. Measures latency, time to first edge and frame time.
//
// Options (iverilog -P tb_top_pipeline.<NAME>=1):
//   GAPS   = 1 : about 25% random idle clocks in the input stream
//   FRAMES = 2 : send a second, different image (coins) straight after the
//                first one with no reset, to check frame-to-frame operation
// ============================================================================
`timescale 1ns/1ps
module tb_top_pipeline;
    parameter W = 128, H = 128, GAPS = 0, FRAMES = 1;
    localparam NIN  = W*H;
    localparam NMED = (W-2)*(H-2);
    localparam NEDG = (W-4)*(H-4);

    reg clk = 0, rst = 1;
    always #5 clk = ~clk;                       // 100 MHz (10 ns)

    reg  [7:0]  pix_in = 0;
    reg         valid_in = 0;
    reg  [10:0] thr = 11'd200;
    wire [7:0]  median_out;
    wire        median_valid, mag_valid, edge_out, edge_valid;
    wire [10:0] mag_out;

    top_pipeline #(.WIDTH(W), .HEIGHT(H)) dut (
        .clk(clk), .rst(rst), .pix_in(pix_in), .valid_in(valid_in), .thr(thr),
        .median_out(median_out), .median_valid(median_valid),
        .mag_out(mag_out), .mag_valid(mag_valid),
        .edge_out(edge_out), .edge_valid(edge_valid));

    // Golden data: frame 1 followed by frame 2
    reg [7:0]  img     [0:2*NIN-1];
    reg [7:0]  exp_med [0:2*NMED-1];
    reg [10:0] exp_mag [0:NEDG-1];
    reg        exp_edg [0:2*NEDG-1];

    integer i, fmed, fedg;
    integer med_idx = 0, med_err = 0, mag_idx = 0, mag_err = 0;
    integer edg_idx = 0, edg_err = 0, edg_count = 0;
    integer cycle = 0, first_in = -1, last_in = -1;
    integer first_med = -1, first_edge = -1, last_edge = -1;
    integer seed = 1;

    always @(posedge clk) cycle <= cycle + 1;

    initial begin
        $readmemh("results/vectors/input_pixels.hex",       img,     0,      NIN-1);
        $readmemh("results/vectors/input_pixels_f2.hex",    img,     NIN,    2*NIN-1);
        $readmemh("results/vectors/expected_median.hex",    exp_med, 0,      NMED-1);
        $readmemh("results/vectors/expected_median_f2.hex", exp_med, NMED,   2*NMED-1);
        $readmemh("results/vectors/expected_mag.hex",       exp_mag);
        $readmemh("results/vectors/expected_edges.hex",     exp_edg, 0,      NEDG-1);
        $readmemh("results/vectors/expected_edges_f2.hex",  exp_edg, NEDG,   2*NEDG-1);
        fmed = $fopen("results/rtl_median.hex", "w");
        fedg = $fopen("results/rtl_edges.hex",  "w");
        if (!GAPS && FRAMES == 1) begin
            $dumpfile("results/tb_top_pipeline.vcd");
            $dumpvars(0, tb_top_pipeline);
        end

        repeat (3) @(posedge clk);
        rst <= 0;
        @(posedge clk);

        for (i = 0; i < FRAMES*NIN; i = i + 1) begin
            if (GAPS) while (($random(seed) & 3) == 0) begin   // about 25% idle cycles
                valid_in <= 0; @(posedge clk);
            end
            pix_in   <= img[i];
            valid_in <= 1;
            if (i == 0)            first_in = cycle;
            if (i == FRAMES*NIN-1) last_in  = cycle;
            @(posedge clk);
        end
        valid_in <= 0;
        repeat (30) @(posedge clk);

        $display("------------------------------------------------------------");
        if (GAPS) $display("Mode            : %0d frame(s), random input gaps ON", FRAMES);
        else      $display("Mode            : %0d frame(s), one pixel every clock", FRAMES);
        $display("Denoised pixels : %0d / %0d received, %0d mismatches", med_idx, FRAMES*NMED, med_err);
        $display("Sobel magnitude : %0d checked (frame 1), %0d mismatches", (mag_idx < NEDG) ? mag_idx : NEDG, mag_err);
        $display("Edge bits       : %0d / %0d received, %0d mismatches", edg_idx, FRAMES*NEDG, edg_err);
        $display("Edge pixels     : %0d marked as edge", edg_count);
        if (!GAPS) begin
            $display("First denoised  : %0d clocks after the first input pixel", first_med - first_in);
            $display("First edge bit  : %0d clocks after the first input pixel", first_edge - first_in);
            $display("Latency         : %0d clocks (last input pixel -> last edge bit)", last_edge - last_in);
            $display("Frame time      : %0d clocks for %0d input pixels", last_edge - first_in + 1, FRAMES*NIN);
        end
        if (med_idx == FRAMES*NMED && edg_idx == FRAMES*NEDG && med_err == 0 && mag_err == 0 && edg_err == 0)
            $display("PASS: full pipeline is bit-exact with the Python reference");
        else
            $display("FAIL");
        $display("------------------------------------------------------------");
        $fclose(fmed); $fclose(fedg);
        $finish;
    end

    // ---- checkers ----
    always @(posedge clk) begin
        if (median_valid) begin
            if (med_idx < NMED) $fwrite(fmed, "%02x\n", median_out);
            if (median_out !== exp_med[med_idx]) med_err = med_err + 1;
            if (first_med < 0) first_med = cycle;
            med_idx = med_idx + 1;
        end
        if (mag_valid) begin
            if (mag_idx < NEDG && mag_out !== exp_mag[mag_idx]) mag_err = mag_err + 1;
            mag_idx = mag_idx + 1;
        end
        if (edge_valid) begin
            if (edg_idx < NEDG) $fwrite(fedg, "%01x\n", edge_out);
            if (edge_out !== exp_edg[edg_idx]) edg_err = edg_err + 1;
            if (edge_out) edg_count = edg_count + 1;
            if (first_edge < 0) first_edge = cycle;
            last_edge = cycle;
            edg_idx = edg_idx + 1;
        end
    end
endmodule
