// ============================================================================
// tb_median.v  -  Unit test for median_filter.v
// Feeds 2000 random 3x3 windows (from python/make_vectors.py) one per clock
// and checks every output against the Python median.
// ============================================================================
`timescale 1ns/1ps
module tb_median;
    localparam N = 2000;
    reg clk = 0, rst = 1;
    always #5 clk = ~clk;                 // 100 MHz clock (10 ns period)

    reg  [7:0] vec [0:N*10-1];            // 9 pixels + expected median per test
    reg  [7:0] w [0:8];
    reg        valid_in = 0;
    wire [7:0] median;
    wire       valid_out;

    median_filter dut (.clk(clk), .rst(rst),
        .w0(w[0]), .w1(w[1]), .w2(w[2]), .w3(w[3]), .w4(w[4]),
        .w5(w[5]), .w6(w[6]), .w7(w[7]), .w8(w[8]),
        .valid_in(valid_in), .median(median), .valid_out(valid_out));

    integer i, k, out_idx = 0, errors = 0;

    initial begin
        $readmemh("results/vectors/median_windows.hex", vec);
        repeat (3) @(posedge clk);
        rst <= 0;
        for (i = 0; i < N; i = i + 1) begin
            @(posedge clk);
            for (k = 0; k < 9; k = k + 1) w[k] <= vec[i*10 + k];
            valid_in <= 1;
        end
        @(posedge clk) valid_in <= 0;
        repeat (10) @(posedge clk);
        if (out_idx != N) begin $display("FAIL: got %0d outputs, expected %0d", out_idx, N); errors = errors + 1; end
        if (errors == 0) $display("PASS: median_filter matched Python on all %0d windows", N);
        else             $display("FAIL: median_filter had %0d errors", errors);
        $finish;
    end

    // Checker: compare each valid output with the expected value
    always @(posedge clk) if (valid_out) begin
        if (median !== vec[out_idx*10 + 9]) begin
            errors = errors + 1;
            if (errors < 10) $display("Mismatch at window %0d: got %0d expected %0d", out_idx, median, vec[out_idx*10+9]);
        end
        out_idx = out_idx + 1;
    end
endmodule
