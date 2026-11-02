# 12 bố cục card

Mọi card có chung: `title` (tiêu đề viết hoa, ≤ 48 ký tự; bỏ trống = card không đầu, sơ đồ lên giữa), `eyebrow` (nhãn nhỏ trên tiêu đề, hợp font `inter`), `note` (chú thích nhỏ cuối card), `start`/`step` (nhịp hiện mặc định). Mục (`items`) thường có `icon`, `label` (1-3 từ), `sub` (dòng nhỏ), `at`, `gold`, `hl` (viền vàng), `dim` (mờ đi).

Icon có sẵn: xem `assets/icons/` (tên lucide: `mail`, `file-text`, `calendar`, `clock`, `check`, `circle-check`, `user`, `users`, `lock`, `lock-open`, `target`, `search`, `shield-check`, `message-square`, `clipboard-list`, `brain`, `lightbulb`, `trending-up`, `chart-column`, `triangle-alert`, `circle-help`, `briefcase`, `repeat`, `hourglass`, `timer`, `gauge`, `scale`, `puzzle`, `stethoscope`, `building-2`…). `render_cards.py --stills` để xem trước toàn bộ.

Xem ví dụ đủ 12 bố cục ở `examples/cards_gallery.json`.

| Bố cục | Dùng khi người nói… | Trường riêng |
|---|---|---|
| `boxes` | liệt kê 2-5 thứ ngang hàng | `items`, `numbered` (01 02 03), `connectors` (gạch nối) |
| `checklist` | kể việc đã xong / chưa xong, đối chiếu với một việc lớn còn treo | `items` (`check: false` để bỏ dấu tích), `panel` {`title`, `bars`, `badge`, `at`} |
| `flow` | A dẫn tới B, chuyển từ cái này sang cái kia | `items` (≥ 2, mũi tên tự vẽ giữa các mục), `ring` (icon trong vòng tròn) |
| `compare` | đối lập hai vế (có thể / cần duyệt, tiến bộ / lặp lại) | `cols` [{`title`, `icon`, `label`, `sub`, `gold`, `dim`, `at`}] |
| `equation` | phép tính, ước lượng (30 phút × 5 ngày = 150 phút) | `terms` [{`value`, `unit`, `sub`, `gold`} hoặc {`op`: "×"}], `track` [{`label`, `w`, `color`: green/gold/dim}], `foot` {`left`, `right`} |
| `bars` | so sánh độ lớn (trách nhiệm vs quyền hạn, trước vs sau) | `items` [{`value`, `label`, `top`, `style`: ""/light/dim}], `maxHeight` |
| `stat` | một con số chính | `value`, `unit`, `sub`, `dial` (mặt đồng hồ, mặc định có), `icon` (thay mặt đồng hồ) |
| `timeline` | trình tự theo thời gian trong ngày/tuần | `items` (dàn đều trên đường kẻ, chấm vàng) |
| `loop` | vòng lặp lặp đi lặp lại (gửi → giải thích → nhắc → leo thang) | `items` (đặt quanh elip, bắt đầu từ trên theo chiều kim đồng hồ), `center` |
| `statement` | một ý/khái niệm đơn | `icon`, `text`, `sub` |
| `chips` | rất nhiều việc vụn vặt lấp kín thời gian, đối lập với một việc quan trọng | `rows` [{`caption`, `chips`: [...]}], `highlight` {`caption`, `icon`, `label`, `other`} |
| `cta` | kêu gọi cuối video | `image`, `l1` (tên), `l2` (FREE · PRIVATE · 2 MIN), `l3` (URL), `l4` (LINK IN DESCRIPTION) |

## Mẹo

- Số trong `value` dạng "30", "2.5", "1,200", "$40" sẽ đếm lên; dạng "2 H 5" chỉ fade.
- Nhãn ngắn, cùng loại từ (danh từ với danh từ). Ba mục là đẹp nhất.
- Card dài > 10 s: cho mục cuối hiện muộn (`at` cao) để card còn "sống".
- Muốn nhấn mạnh một mục: `gold: true` (chữ/icon vàng) hoặc `hl: true` (viền vàng, chỉ `boxes`).
- `chips` cần chữ ngắn (1 từ) và 6-10 chip một hàng.
