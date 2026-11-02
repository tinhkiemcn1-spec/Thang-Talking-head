# Phân tích bộ mẫu (redshort, greenshort, greyshort)

Ba video cùng một người nói, cùng một bộ nhận diện; khác màu áo và biến thể font. Số liệu đo từ chính file mẫu (ffprobe, ebur128, contact sheet mỗi 10 s và mỗi 0,25 s ở các đoạn chuyển).

## Thông số

| | redshort | greenshort | greyshort |
|---|---|---|---|
| Thời lượng | 7:37 | 6:59 | 7:27 |
| Hình | 1920×1080, 30 fps, H.264 | như trên | như trên |
| Âm | AAC 48 kHz stereo | như trên | như trên |
| Loudness | −16,2 LUFS | −22,2 LUFS | −20,7 LUFS |
| LRA | 4,4 LU | 4,5 LU | 4,3 LU |

Tên có chữ "short" nhưng là video ngang 7 phút. Loudness mẫu không đều: skill chuẩn hóa về −14 LUFS (YouTube), true peak −1 dB. LRA ≈ 4 nghĩa là giọng đã nén khá chặt: dùng compressor nhẹ (ratio 3).

## Footage

- Một người nói, ngồi sofa, tường giấy dán hoa văn hình học trắng. Quay điện thoại góc rộng, đầu ở 1/3 trên khung.
- 2 góc máy: chính diện (chính, khoảng 2/3 thời lượng) và nghiêng ~45° (phụ). Đổi góc tại điểm cắt để giấu jump cut.
- Ánh sáng phòng, hơi nhiễu nhẹ: denoise rất nhẹ nếu cần.

## Màu

Sạch, tự nhiên, không "look": tường trắng hơi kem (không xanh, không vàng), da ấm thật, tương phản +4-8%, bão hòa +3%. Màu áo (đỏ/xanh rêu/xám) giữ đúng. Hai góc máy phải khớp màu tường và da. → `grade.py` mặc định đã làm đúng như vậy.

## Cắt

- Bỏ khoảng lặng dài, từ đệm, câu nói lại; giữ nhịp nói tự nhiên (pause ngắn < 0,6 s giữ lại).
- Chuyển cảnh người ↔ card và người ↔ B-roll: hòa tan (cross-dissolve) khoảng 0,3-0,4 s. Người ↔ người: cắt thẳng.
- Nhịp: cứ 20-40 s có một lần đổi hình (card, B-roll hoặc đổi góc). Card + B-roll phủ khoảng 30-40% thời lượng.

## Chữ chốt (không phải phụ đề)

- Không có phụ đề chạy cả bài. Chỉ có câu chốt 3-8 từ, viết hoa, chữ trắng đậm, bóng đổ mềm.
- Vị trí: giữa dưới (phổ biến), hoặc góc trên trái cỡ lớn làm hook mở đầu ("RESPONSIBLE. BUT NO CONTROL.").
- Hiện/ẩn bằng fade, đứng 3-5 s, chỉ trên cảnh người nói.
- Ví dụ: "YOUR BEST THINKING IS STILL WAITING.", "TOO LITTLE ROOM TO DO THE WORK?", "THE WORK - OR THE UNCERTAINTY?", "SOLVING — OR SEEKING PERMISSION?". Câu hỏi tu từ và đối lập hai vế là kiểu đặc trưng.

## Card đồ họa

**Nền**: gradient navy (#0f1429) → tím đậm (#2b2156), sáng dần về góc dưới phải. **Nhấn**: vàng gold (#c9a45c), thỉnh thoảng xanh rêu (#3d7a6c) cho thanh "được bảo vệ". **Chữ**: trắng, viết hoa; phụ đề nhỏ màu xám tím (#8a90b4) giãn chữ rộng.

**Đầu card**: (eyebrow nhỏ, chỉ bản Inter) → tiêu đề viết hoa → đường kẻ mảnh toàn chiều ngang. Một số card không có tiêu đề (greyshort): chỉ sơ đồ ở giữa.

**Biến thể font**: redshort dùng sans gọn kiểu Inter + eyebrow ("THE RECOGNITION", "THE CAPACITY GAP"); green/grey dùng chữ hẹp kiểu Oswald, không eyebrow.

**Thành phần lặp lại**: icon nét mảnh (phong bì, tài liệu, lịch, đồng hồ, dấu tích, người, ổ khóa, kính lúp, bia ngắm, khiên); ô viền mảnh bo góc; mũi tên vàng; đường timeline có chấm vàng; số lớn; thanh tiến độ; biểu đồ cột vàng/trắng; mặt đồng hồ; vòng lặp elip. Ghi chú nhỏ cuối card: "ILLUSTRATIVE ESTIMATE", "CONCEPTUAL ILLUSTRATION", "NOT SHOWN ON THE PERFORMANCE REPORT".

**Chuyển động**: nền hiện trước, tiêu đề fade + trượt lên, đường kẻ chạy từ trái, rồi từng mục hiện lần lượt **đúng lúc người nói nhắc tới**; mũi tên tự vẽ; số đếm lên; thanh trượt dài ra. Sau đó đứng yên tới hết ý. Không zoom, không xoay, không particle.

**Nội dung**: tóm ý người nói thành 1 tiêu đề (≤ 7 từ) + 2-4 nhãn (1-3 từ). Số liệu chỉ khi người nói nêu, ví dụ thì ghi "Illustrative estimate".

## B-roll

Stock footage văn phòng/doanh nhân/họp (greenshort, greyshort), 4-6 s, đặt khi người nói kể tình huống ("Imagine a senior healthcare leader…"). Không B-roll ở redshort: tùy video.

## Thương hiệu

- Logo đôi cánh góc trên phải suốt video, kể cả trên card, rộng ~150 px, lề ~30 px.
- Card kêu gọi cuối (green/grey): "THE CLARITY QUIZ" + ảnh quiz + "FREE · PRIVATE · 2 MIN" + URL + "LINK IN DESCRIPTION".
- Outro logo nhà xuất bản (redshort) hòa tan vào cuối.

## Ánh xạ sang skill

| Mẫu | Skill |
|---|---|
| Cắt khoảng lặng/nói lại | `rough_cut.py` |
| 2 góc máy | `sync.py` + `cam` trong segments |
| Màu | `grade.py` |
| Âm thanh −14 LUFS | `render.py` (voice chain + loudnorm 2 lượt) |
| Card | `render_cards.py` + `templates/` (12 bố cục) |
| Chữ chốt | `captions` (layout caption) |
| B-roll | `fetch_broll.py` / clip khách + `broll` |
| Logo, card kêu gọi, outro | `logo`, card `cta`, `outro` |
| Timeline chỉnh tiếp | `resolve_build.py` |
