// ============================================================================
// window_buffer.v
// Turns a stream of pixels (one per clock, row by row) into a 3x3 window.
//
// How it works:
//   - Two line buffers remember the previous two image rows.
//   - Each clock, one new column {row y-2, row y-1, row y} enters the window
//     from the right and the oldest column falls off the left.
//   - The window is "valid" only when it lies fully inside the image
//     (row >= 2 and column >= 2). Border pixels produce no output.
//
// Window layout (w0 = top-left, w8 = bottom-right):
//     w0 w1 w2
//     w3 w4 w5
//     w6 w7 w8
// ============================================================================
module window_buffer #(
    parameter WIDTH  = 128,   // image width in pixels
    parameter HEIGHT = 128    // image height in pixels
)(
    input  wire       clk,
    input  wire       rst,        // synchronous reset, active high
    input  wire [7:0] pix_in,     // incoming pixel
    input  wire       valid_in,   // pix_in is a real pixel this clock
    output reg  [7:0] w0, w1, w2, w3, w4, w5, w6, w7, w8,
    output reg        valid_out   // window is complete and inside the image
);
    // Line buffers: previous row (lb_mid) and the row before it (lb_top).
    reg [7:0] lb_top [0:WIDTH-1];
    reg [7:0] lb_mid [0:WIDTH-1];

    // Position of the incoming pixel
    reg [$clog2(WIDTH)-1:0]  col;
    reg [$clog2(HEIGHT):0]   row;

    // Values read from the line buffers for the current column
    wire [7:0] top = lb_top[col];
    wire [7:0] mid = lb_mid[col];

    always @(posedge clk) begin
        if (rst) begin
            col       <= 0;
            row       <= 0;
            valid_out <= 1'b0;
        end else begin
            valid_out <= 1'b0;
            if (valid_in) begin
                // 1) Update line buffers: rows move up by one
                lb_top[col] <= mid;
                lb_mid[col] <= pix_in;

                // 2) Shift the 3x3 window left and insert the new column
                w0 <= w1;  w1 <= w2;  w2 <= top;
                w3 <= w4;  w4 <= w5;  w5 <= mid;
                w6 <= w7;  w7 <= w8;  w8 <= pix_in;

                // 3) Window is valid once 3 rows and 3 columns are available
                valid_out <= (row >= 2) && (col >= 2);

                // 4) Advance column / row counters
                if (col == WIDTH-1) begin
                    col <= 0;
                    row <= (row == HEIGHT-1) ? 0 : row + 1;  // wrap for next frame
                end else begin
                    col <= col + 1;
                end
            end
        end
    end
endmodule
