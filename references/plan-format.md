# plan.json

Một file mô tả toàn bộ video. `sync.py`, `transcribe.py`, `rough_cut.py`, `grade.py` tự ghi các phần của chúng; Claude viết `cards`, `captions`, `broll`, `logo`… Mọi đường dẫn tương đối tính từ thư mục `<edit>`.

**Hai đồng hồ:**
- `segments[].in/out` tính bằng giây của **máy A** (nguồn).
- Mọi thứ khác (`cards`, `captions`, `broll`) tính bằng giây của **video đầu ra**, lấy từ `timeline.md` / `timeline_words.json`.

```json
{
  "fps": 30, "width": 1920, "height": 1080,
  "font": "inter",
  "fade": 0.35,

  "sources": {"A": "D:/shoot/front.mp4", "B": "D:/shoot/side.mp4"},
  "offsets": {"B": 2.5},
  "grade": {"A": "colorchannelmixer=...,eq=...", "B": "...", "broll": "eq=saturation=0.9"},

  "segments": [
    {"src": "A", "in": 0.00, "out": 11.52, "cam": "A"},
    {"src": "A", "in": 11.52, "out": 26.30, "cam": "B"},
    {"src": "A", "in": 27.10, "out": 35.00, "cam": "A", "zoom": 1.12, "zoom_y": 0.3}
  ],

  "cards": [
    {"t": 10.0, "end": 20.0, "layout": "compare", "eyebrow": "The uncomfortable question",
     "title": "Too much work, or too little room?", "sfx": "whoosh",
     "cols": [{"icon": "layers", "title": "Too much work", "dim": true},
              {"icon": "calendar", "title": "Too little room", "gold": true, "at": 3.5}]}
  ],
  "captions": [
    {"t": 26.4, "end": 31.2, "text": "Being occupied is not progress.", "pos": "bottom"},
    {"t": 0.3, "end": 5.0, "text": "Busy.\nStill waiting.", "pos": "top-left"}
  ],
  "broll": [
    {"t": 50.0, "end": 55.5, "file": "broll/office.mp4", "src": 2.0}
  ],

  "logo": {"file": "logo.png", "width": 150, "pos": "tr", "margin": 32, "opacity": 0.9},
  "music": {"file": "music.mp3", "db": -26},
  "outro": {"file": "outro.mp4"},
  "audio": {"highpass": 80, "denoise": 10, "deess": true, "compress": true, "lufs": -14}
}
```

## Trường

| Trường | Ý nghĩa |
|---|---|
| `font` | `inter` (eyebrow, giống redshort) hoặc `oswald` (chữ hẹp, giống green/grey) |
| `fade` | giây hòa tan khi card/B-roll vào và ra |
| `sources` | `A` bắt buộc (lấy âm thanh), `B` tùy chọn |
| `offsets.B` | `B_time = A_time + offset` (sync.py tính) |
| `grade.<cam>` | chuỗi filter ffmpeg; `grade.broll` áp cho mọi B-roll |
| `segments[].cam` | góc hình của đoạn; âm luôn là A |
| `segments[].zoom` | punch-in (1.08-1.2) để giấu jump cut khi chỉ có 1 máy; `zoom_y` 0 = giữ mép trên, 0.5 = giữa |
| `cards[]` | `t`, `end` (giây output), `layout`, nội dung theo `card-layouts.md`; tùy chọn `id`, `fade`, `sfx` (`whoosh`, `pop`, `tick`, `ding`), `sfx_db` (mặc định −16) |
| `cards[].start` / `step` | giờ mục đầu tiên hiện và khoảng cách giữa các mục khi không ghi `at` (mặc định 0.8 s / 0.45 s) |
| `cards[].items[].at` | giây (tính từ đầu card) mục đó hiện; lấy lúc từ khóa được nói |
| `cards[].note` | dòng chú thích nhỏ cuối card; `noteLeft: true` để căn trái |
| `captions[]` | `text` (xuống dòng bằng `\n`), `pos`: `bottom` / `top-left` / `center` |
| `broll[]` | `file`, `src` (giây bắt đầu trong clip), `fade` |
| `logo` | chuỗi đường dẫn hoặc object; `pos`: `tr`, `tl`, `br`, `bl` |
| `music` | nhạc nền lặp, mặc định −26 dB, fade đầu/cuối |
| `outro` | clip nối sau cùng với hòa tan 0,5 s |
| `audio` | voice chain; `denoise` 0 = tắt, 15-20 = phòng ồn |

## Tính `at` cho từng mục

`timeline_words.json` là danh sách `{"o": giây output, "d": độ dài, "w": từ}`. Mục "Analysis" của card bắt đầu lúc `t = 31.6` mà người nói nói "analysis" ở `o = 37.0` → `"at": 5.4`. Đặt `at` sớm hơn từ khóa 0,1-0,2 s để mắt kịp thấy khi tai nghe.
