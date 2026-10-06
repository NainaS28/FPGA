// ============================================================================
// tb_median_stream.v  -  Streams a whole image through the Phase 1 hardware.
//
// 1. Feeds the noisy 128x128 cameraman image (input_pixels.hex) into
//    median_stream, one pixel per clock.
// 2. Compares every denoised pixel with the Python result.
// 3. Writes the hardware output to results/rtl_median.hex (to rebuild the image).
// 4. Measures latency and total clock cycles.
//
// Set GAPS=1 (iverilog -P tb_median_stream.GAPS=1) to insert random idle
// cycles in the input. This checks that the valid signals handle pauses.
// ============================================================================
`timescale 1ns/1ps
module tb_median_stream;
    parameter W = 128, H = 128, GAPS = 0;
    localparam NIN  = W*H;
    localparam NMED = (W-2)*(H-2);

    reg clk = 0, rst = 1;
    always #5 clk = ~clk;                       // 100 MHz (10 ns)

    reg  [7:0] pix_in = 0;
    reg        valid_in = 0;
    wire [7:0] median_out;
    wire       median_valid;

    median_stream #(.WIDTH(W), .HEIGHT(H)) dut (
        .clk(clk), .rst(rst), .pix_in(pix_in), .valid_in(valid_in),
        .median_out(median_out), .median_valid(median_valid));

    reg [7:0] img     [0:NIN-1];
    reg [7:0] exp_med [0:NMED-1];

    integer i, fmed;
    integer med_idx = 0, med_err = 0;
    integer cycle = 0, first_in = -1, last_in = -1, first_out = -1, last_out = -1;
    integer seed = 1;

    always @(posedge clk) cycle <= cycle + 1;

    initial begin
        $readmemh("results/vectors/input_pixels.hex",    img);
        $readmemh("results/vectors/expected_median.hex", exp_med);
        fmed = $fopen("results/rtl_median.hex", "w");
        $dumpfile("results/tb_median_stream.vcd");
        $dumpvars(0, tb_median_stream);

        repeat (3) @(posedge clk);
        rst <= 0;
        @(posedge clk);

        // ---- stream the image in, one pixel per clock ----
        for (i = 0; i < NIN; i = i + 1) begin
            if (GAPS) while (($random(seed) & 3) == 0) begin   // about 25% idle cycles
                valid_in <= 0; @(posedge clk);
            end
            pix_in   <= img[i];
            valid_in <= 1;
            if (i == 0)     first_in = cycle;
            if (i == NIN-1) last_in  = cycle;
            @(posedge clk);
        end
        valid_in <= 0;
        repeat (20) @(posedge clk);

        // ---- report ----
        $display("------------------------------------------------------------");
        $display("Denoised pixels : %0d / %0d received, %0d mismatches", med_idx, NMED, med_err);
        $display("First output    : %0d clock cycles after the first input pixel", first_out - first_in);
        $display("Latency         : %0d clock cycles (last input -> last output)", last_out - last_in);
        $display("Frame time      : %0d clock cycles for %0d input pixels", last_out - first_in + 1, NIN);
        if (med_idx == NMED && med_err == 0)
            $display("PASS: hardware median is bit-exact with the Python reference");
        else
            $display("FAIL");
        $display("------------------------------------------------------------");
        $fclose(fmed);
        $finish;
    end

    // ---- checker ----
    always @(posedge clk) if (median_valid) begin
        $fwrite(fmed, "%02x\n", median_out);
        if (median_out !== exp_med[med_idx]) med_err = med_err + 1;
        if (first_out < 0) first_out = cycle;
        last_out = cycle;
        med_idx = med_idx + 1;
    end
endmodule
