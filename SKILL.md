---
name: thang-talking-head
description: Dựng video talking-head kiểu giáo dục/coaching (người nói ngồi trước camera, 1-2 góc máy, xen card đồ họa nền xanh navy chữ trắng điểm vàng, chữ chốt viết hoa, B-roll, logo góc, card kêu gọi cuối) từ footage thô đến file cuối và timeline DaVinci Resolve. Chép lời theo từ, cắt khoảng lặng/từ đệm/câu nói lại, đồng bộ và đổi góc máy, chỉnh màu tự nhiên, lọc và chuẩn hóa âm thanh, tạo đồ họa động bằng code (HTML) khớp với lời nói. Dùng khi người dùng gõ /thang-talking-head, "talking head", "dựng video người nói", "làm giống redshort/greenshort/greyshort", video khách kiểu coaching/leadership/podcast một người có card minh họa.
---

# Thang Talking-head

Footage thô của một người nói → video 1080p30 giống bộ mẫu (redshort, greenshort, greyshort): cắt gọn, đổi góc, màu sạch, card đồ họa động khớp lời nói, chữ chốt, B-roll, logo, card kêu gọi, âm thanh −14 LUFS. Đồ họa hoàn toàn bằng code nên sửa chữ, màu, nhịp đều nhanh và lặp lại được.

Trước khi lên plan, đọc `references/phan-tich-mau.md` (phong cách mẫu, số liệu nhịp), `references/plan-format.md` (định dạng plan.json) và `references/card-layouts.md` (12 bố cục card, khi nào dùng cái nào).

## Quy tắc cứng

1. **Âm thanh luôn lấy từ máy A** (máy chính), kể cả khi hình là máy B. Không kéo giãn, không đổi tốc độ lời nói.
2. **Không cắt giữa từ.** Mọi điểm cắt bám ranh giới từ trong transcript, có đệm 30-200 ms, fade âm 30 ms ở mỗi điểm cắt (render.py tự làm).
3. **Không bịa nội dung.** Chữ, số trên card và chữ chốt phải đến từ lời người nói. Ví dụ minh họa thì ghi `"eyebrow": "Illustrative estimate"` như mẫu. Không chắc thì hỏi.
4. **Duyệt trước khi render dài.** Cắt thô → người dùng xác nhận các đoạn bỏ; card → xem `cards/_sheet.jpg` trước; luôn `--preview` trước bản cuối.
5. **Chữ chốt chỉ đặt trên cảnh người nói**, không trùng card (check_plan báo lỗi).
6. **Không ghi đè.** render.py tự đặt `final_v2.mp4`…; resolve_build.py tự đặt tên timeline mới.
7. **B-roll có giấy phép**: clip người dùng đưa, hoặc Pexels qua `fetch_broll.py` (giữ `broll/credits.csv`). Logo, ảnh quiz, outro là tài sản của khách: chỉ dùng file khách đưa.
8. **Tự kiểm tra trước khi đưa người dùng xem**: chạy `sheet.py` trên bản render, nhìn sheet, đọc loudness.

## Chuẩn bị

Script ở `scripts/` của skill, chạy `python -X utf8 <script>`. Thư mục làm việc `<edit>` do người dùng chọn (mặc định `<thư mục footage>/edit`). Cần ffmpeg trong PATH, `pip install -r requirements.txt`, `python -m playwright install chromium` (install.py làm hết).

Hỏi người dùng (gộp một lần, chỉ hỏi cái chưa biết):
- File máy A (bắt buộc), máy B (nếu có).
- Logo khách (PNG nền trong), link/ảnh card kêu gọi cuối video, outro (nếu có).
- Font: `inter` (giống redshort, có eyebrow nhỏ) hay `oswald` (chữ hẹp, giống green/grey).
- Có B-roll không (clip của khách hay lấy Pexels, cần `PEXELS_API_KEY`), có nhạc nền không.
- Ngôn ngữ lời nói, độ dài mong muốn.

## Quy trình

1. **Xem footage**: `sheet.py <camA> --every 20` (nhìn khung hình, âm lượng gốc). Có video mẫu mới của khách thì chạy `sheet.py` trên mẫu và đối chiếu với `references/phan-tich-mau.md`.
2. **Đồng bộ 2 máy** (nếu có B): `sync.py <camA> <camB> --edit <edit>` → ghi `sources` + `offsets` vào plan.json. Độ tin cậy < 0.15 thì kiểm tra bằng mắt. Chỉ có 1 máy: bỏ qua, bước 3 tự tạo plan.json với máy A.
3. **Chép lời**: `transcribe.py <camA> <edit> --lang en` (thêm `--prompt "tên riêng"`; `--model small` cho bản nháp nhanh, `large-v3` cho bản cuối).
4. **Cắt thô**: `rough_cut.py <edit>` → đọc `cut_review.md`. Báo người dùng ngắn gọn: thời lượng trước/sau, các câu nói lại bị bỏ. Sửa tay `segments` trong plan.json nếu cần (bỏ đoạn lạc đề, giữ câu bị nhận nhầm là nói lại), rồi `rough_cut.py <edit> --text` để dựng lại `timeline.md`. Một máy mà jump cut lộ: thêm `"zoom": 1.12` cho đoạn sau điểm cắt (punch-in).
5. **Màu**: `grade.py <edit>` → xem `grade/compare.jpg` (trên gốc, dưới đã chỉnh). Da phải ấm tự nhiên, tường trắng trung tính, màu áo giữ nguyên. Cần thêm: `--look warm`, `--look punch+denoise`… (xem `--print-looks`). Sửa tay `grade` trong plan được.
6. **Lên plan đồ họa** từ `timeline.md` (mốc thời gian là đồng hồ OUTPUT) và `timeline_words.json` (mốc từng từ):
   - Card: khoảng 1 card mỗi 20-40 s, dài 5-15 s, phủ 30-40% thời lượng. Card bắt đầu ở đầu câu mở ý, kết thúc khi ý đó nói xong. Mỗi mục trong card hiện đúng lúc từ đó được nói (`"at"` = giây tính từ đầu card, lấy từ timeline_words.json).
   - Chữ chốt: 4-8 câu/video, câu đắt nhất (luận điểm, câu hỏi tu từ), 3-8 từ, đặt trên cảnh người nói, 3-5 s. Hook mở đầu có thể dùng `"pos": "top-left"`.
   - B-roll: 0-6 đoạn 4-6 s ở chỗ người nói kể ví dụ/tình huống.
   - Card kêu gọi (`cta`) 10-20 s cuối nếu khách có quiz/link.
   - Ghi vào plan.json (định dạng ở `references/plan-format.md`), rồi `check_plan.py <edit>` đến khi `PLAN OK`.
7. **Đồ họa**: `render_cards.py <edit> --stills` → xem `cards/_sheet.jpg` (chữ tràn, icon sai, bố cục lệch). Sửa plan, rồi `render_cards.py <edit>` (có cache, chỉ render card đã đổi).
8. **Preview**: `render.py <edit> --preview` → `sheet.py <edit>/preview.mp4 --every 5`. Nhìn: card che đúng lúc, chữ chốt không trùng card, góc máy đổi hợp lý, logo ở góc. Đưa người dùng xem preview, sửa theo góp ý (lặp bước 6-8).
9. **Bản cuối**: `render.py <edit>` → `final.mp4`. Kiểm tra lại bằng `sheet.py` (loudness phải ≈ −14 LUFS).
10. **DaVinci Resolve** (khi người dùng muốn chỉnh tiếp trong Resolve): `resolve_build.py <edit> --name "<tên>"`. Bản Free: chạy `resolve_build.py install-script` một lần, rồi trong Resolve chọn Workspace > Scripts > Thang Talking-head Build.

## Khi người dùng muốn khác mẫu

Mọi màu, font, cỡ chữ của card nằm ở biến CSS đầu `templates/card.css`; đổi theme khách = đổi các biến đó. Bố cục mới = thêm một hàm vào `LAYOUTS` trong `templates/card.js` (dùng `anim(el, at, fx)` cho chuyển động) và thêm tên vào `LAYOUTS` của `check_plan.py`. Icon thêm: tải SVG từ lucide-static vào `assets/icons/`.

## Xử lý sự cố

- `transcribe.py` báo thiếu cublas: tự chuyển CPU, chỉ chậm hơn.
- Card trắng/thiếu font: chạy lại `python -m playwright install chromium`.
- Resolve không kết nối: bản Free hoặc chưa bật External scripting = Local; dùng menu script.
- ffmpeg cũ (< 7) vẫn chạy được: script tự đổi cờ đọc filtergraph.
