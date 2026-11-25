// ============================================================================
// tb_sobel.v  -  Unit test for sobel_filter.v
// Feeds 2000 3x3 windows (from python/make_vectors.py), one per clock, and
// checks every magnitude |Gx|+|Gy| against Python. The set includes the
// extreme cases: maximum +Gx, -Gx, +Gy, -Gy, all zero and the largest possible magnitude, 1530.
// ============================================================================
`timescale 1ns/1ps
module tb_sobel;
    localparam N = 2000;
    reg clk = 0, rst = 1;
    always #5 clk = ~clk;                 // 100 MHz clock (10 ns period)

    reg  [10:0] vec [0:N*10-1];           // 9 pixels + expected magnitude per test
    reg  [7:0]  w [0:8];
    reg         valid_in = 0;
    wire [10:0] mag;
    wire        valid_out;

    sobel_filter dut (.clk(clk), .rst(rst),
        .w0(w[0]), .w1(w[1]), .w2(w[2]), .w3(w[3]), .w4(w[4]),
        .w5(w[5]), .w6(w[6]), .w7(w[7]), .w8(w[8]),
        .valid_in(valid_in), .mag(mag), .valid_out(valid_out));

    integer i, k, out_idx = 0, errors = 0, max_seen = 0;

    initial begin
        $readmemh("results/vectors/sobel_windows.hex", vec);
        repeat (3) @(posedge clk);
        rst <= 0;
        for (i = 0; i < N; i = i + 1) begin
            @(posedge clk);
            for (k = 0; k < 9; k = k + 1) w[k] <= vec[i*10 + k][7:0];
            valid_in <= 1;
        end
        @(posedge clk) valid_in <= 0;
        repeat (5) @(posedge clk);
        $display("------------------------------------------------------------");
        $display("Sobel unit test : %0d / %0d windows checked, %0d mismatches", out_idx, N, errors);
        $display("Largest magnitude seen: %0d (largest possible for 8-bit pixels: 1530)", max_seen);
        if (out_idx == N && errors == 0) $display("PASS: sobel_filter matches the Python model");
        else                             $display("FAIL");
        $display("------------------------------------------------------------");
        $finish;
    end

    always @(posedge clk) if (valid_out) begin
        if (mag !== vec[out_idx*10 + 9]) begin
            errors = errors + 1;
            if (errors <= 5) $display("  mismatch at window %0d: got %0d, expected %0d",
                                      out_idx, mag, vec[out_idx*10 + 9]);
        end
        if (mag > max_seen) max_seen = mag;
        out_idx = out_idx + 1;
    end
endmodule
