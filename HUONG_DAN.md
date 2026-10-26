# Auto Video — bổ sung phông chữ

## Cách dùng trên Windows

1. Giải nén TOÀN BỘ file ZIP vào một thư mục mới để giữ nguyên bản cũ.
2. Máy cần có Python 3.10 trở lên kèm Tcl/Tk (bản cài chuẩn từ python.org có sẵn). Khi cài Python, chọn “Add Python to PATH”.
3. Mở `CAI_DAT.bat` một lần để cài các thư viện. Bước này cần Internet.
4. Mở `RUN_TOOL.bat` để chạy `app.py`.
5. Vào tab **3. Tùy Chỉnh Chữ (Style)**, chọn **Phông chữ (Font)**. Ô mẫu cập nhật theo font đã chọn; trong `app.py`, màn hình preview bên phải cũng cập nhật.
6. Chọn video/ảnh và âm thanh như trước, nhập chữ rồi bấm **XEM NHÁP** hoặc tạo video. Nếu máy không có GPU NVIDIA phù hợp, bỏ chọn chế độ GPU.

Không tách riêng `app.py`: cần giữ `font_support.py` và thư mục `fonts` cạnh nó. Font kèm sẵn không cần cài vào Windows hay quyền quản trị. Video đã xuất có chữ được render sẵn nên người xem không cần cài font. Thư viện imageio-ffmpeg cung cấp FFmpeg.

## Các phông kèm sẵn

- **Be Vietnam Pro**: rõ dấu tiếng Việt, hợp phụ đề và nội dung thông thường; có Regular và Bold.
- **Kanit**: nét hiện đại, hợp tiêu đề; có Regular và Bold.
- **Anton**: chữ đậm, cao, hợp tiêu đề nổi bật.
- **Lobster**: chữ viết tay kiểu trang trí.
- **Pacifico**: chữ viết tay mềm mại.
- **Pattaya**: chữ nghiêng trang trí.

Đây là các phông miễn phí có phong cách tương tự chữ thường dùng trong video CapCut; không phải toàn bộ thư viện font hoặc hiệu ứng của CapCut. Chúng hỗ trợ tiếng Việt. Công cụ còn liệt kê các font thực tế có trên máy; để thêm font riêng, cài TTF/OTF tin cậy vào Windows và mở lại công cụ.

## Những tệp đã cập nhật

`app.py` và `app_v2.py`: danh sách font kèm sẵn và font trên máy, mẫu tiếng Việt, nạp font cho FFmpeg. `RUN_TOOL.bat`: luôn chạy từ đúng thư mục, kể cả mở bằng shortcut. `font_support.py`, `fonts`, `requirements.txt` và `CAI_DAT.bat` là các phần bổ sung.

`app_gui.py`, `auto_video.py` và `text.txt` được giữ nguyên từ bản bạn gửi; hai chương trình cũ này không có bộ chọn font mới. Launcher mặc định chạy bản `app.py` đầy đủ hơn.

## Kiểm tra

Đã kiểm tra hai GUI bằng Tk 8.6 trên Linux với màn hình ảo; chọn đủ 6 font và xác nhận font thực tế trên canvas. Đã render chữ tiếng Việt với FFmpeg đi kèm imageio-ffmpeg cho đủ 6 font, xác nhận mỗi font được chọn đúng và hình ảnh khác nhau. Đã thử đường dẫn có dấu, dấu nháy, khoảng trắng, dấu phẩy và dấu hai chấm.

Chưa kiểm tra trực tiếp trên Windows hoặc render video dài với GPU của bạn. Phần nạp font trên Windows dùng API AddFontResourceExW của Windows.

## Nguồn và giấy phép font

Google Fonts, giấy phép SIL Open Font License; từng giấy phép được giữ trong `fonts/<tên họ>/OFL.txt`. Nguồn, commit và SHA-256 từng tệp nằm trong `fonts/SOURCES.json`. Không cần tải font khi chạy ứng dụng.
