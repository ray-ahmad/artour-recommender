# ARTour Recommender API

Microservice FastAPI untuk rekomendasi ARTour dengan dua endpoint utama:

- `POST /recommend/user-to-item`
- `GET /recommend/item-to-item/{id}`

Layanan ini mengadopsi standar **Clean Architecture (src-layout)** yang selaras dengan backend microservice Temas:

- `cmd/server/`: Entrypoint bootstrapping aplikasi (`python -m cmd.server.main`)
- `src/config/`: Sentralisasi konfigurasi dan binding environment variables (`src.config.settings`)
- `src/adapter/`:
  - `handlers/`: HTTP Controllers/Handlers (`health_handler`, `admin_handler`, `recommendation_handler`)
  - `presenter/`: Response formatter & payload envelopes (`src.adapter.presenter.response`)
  - `routes/`: Routing aggregation (`init_routes()`)
- `src/entity/`: DTOs, request & response schemas (`recommendation_dto`, `admin_dto`, `model_dto`)
- `src/module/recommendation/`:
  - `repository.py`: Pemuatan data dari backend ARTour
  - `service.py`: Core logic orchestrator rekomendasi
  - `refresh_job.py`: Asynchronous background refresh job
  - `algorithms/`: Sub-engine rekomendasi (`apriori`, `cbf`, `mcrs`, `text_preprocessor`)
- `src/clients/`: Integrasi eksternal (`webhook_client.py`)
- `src/infrastructure/`:
  - `server/`: Factory FastAPI engine, lifespan, exception handler (`src.infrastructure.server.rest`)
  - `middlewares/`: Correlation ID middleware & logger filter
- `src/shared/`: Shared exceptions & utilities

## Alur Data

Repository mengambil JSON dari endpoint backend ARTour:

- `/places`
- `/user-interactions`

Payload tersebut langsung dikonversi menjadi DataFrame pandas di memori. API ini tidak membaca maupun menulis file CSV sama sekali.

## Perilaku saat Startup

Saat startup, aplikasi otomatis mencoba melakukan refresh. Apabila backend belum dapat diakses, layanan tetap berjalan, namun status health-nya "belum siap" hingga `/refresh` berhasil.

Endpoint `/refresh` menerima `refreshId` opsional, langsung membalas `202 Accepted`, kemudian menyelesaikan proses refresh di background sebelum mengirim webhook callback ke NestJS. Apabila `ARTOUR_REFRESH_TRIGGER_TOKEN` diset, request wajib menyertakan header `X-ARTOUR-REFRESH-TRIGGER-TOKEN`.

## Menjalankan Layanan

```bash
uvicorn src.infrastructure.server.rest:app --reload
```

Atau menggunakan runner CLI:
```bash
python -m cmd.server.main
```

## Environment Variables

- `ARTOUR_BACKEND_BASE_URL`
- `ARTOUR_PLACES_PATH`
- `ARTOUR_USER_INTERACTIONS_PATH`
- `ARTOUR_MIN_POSITIVE_RATING`
- `ARTOUR_REQUEST_TIMEOUT_SECONDS`
- `ARTOUR_REFRESH_WEBHOOK_URL`
- `ARTOUR_REFRESH_TRIGGER_TOKEN`
- `ARTOUR_REFRESH_WEBHOOK_TOKEN`
- `ARTOUR_REFRESH_WEBHOOK_TIMEOUT_SECONDS`
- `ARTOUR_APRIORI_ABSOLUTE_SUPPORT`
- `ARTOUR_APRIORI_MIN_USER_INTERACTIONS`
- `ARTOUR_APRIORI_MAX_LEN`
- `ARTOUR_MCRS_MIN_RATING_SCALE`
- `ARTOUR_MCRS_MAX_RATING_SCALE`
- `ARTOUR_DEFAULT_K`
- `ARTOUR_DEFAULT_N`
- `ARTOUR_MAX_USER_BASKET_SIZE`
- `ARTOUR_WEIGHT_COST`
- `ARTOUR_WEIGHT_BENEFIT`
- `ARTOUR_RECOMMENDATION_STATE_PATH`

## Environment di Hugging Face Spaces

File `.env` sengaja di-ignore karena bersifat khusus untuk lingkungan lokal. Di Hugging Face Spaces, environment diisi melalui **Settings > Variables and secrets**:

- Gunakan **Variables** untuk nilai biasa seperti `ARTOUR_BACKEND_BASE_URL`.
- Gunakan **Secrets** untuk token atau credential seperti `ARTOUR_REFRESH_TRIGGER_TOKEN` dan `ARTOUR_REFRESH_WEBHOOK_TOKEN`.

Contoh minimum untuk Space:

```text
ARTOUR_BACKEND_BASE_URL=https://artour-api.hf.space
ARTOUR_REFRESH_WEBHOOK_URL=
ARTOUR_REFRESH_TRIGGER_TOKEN=
ARTOUR_REFRESH_WEBHOOK_TOKEN=
```

Apabila backend API belum di-deploy atau masih bersifat private, Space ini akan tetap berjalan, tetapi endpoint recommendation belum siap digunakan hingga `ARTOUR_BACKEND_BASE_URL` valid dan `/refresh` berhasil.

## Contoh Request

### User-to-item

```bash
curl -X POST http://localhost:8000/recommend/user-to-item \
  -H 'Content-Type: application/json' \
  -d '{"basketIds":["p1","p2","p3"],"k":5}'
```

### Item-to-item

```bash
curl http://localhost:8000/recommend/item-to-item/p1?k=5
```

## Catatan

- User-to-item menambal hasil Apriori yang kosong dengan CBF, menggunakan centroid dari seluruh basket.
- Item-to-item menambal hasil Apriori yang kosong dengan CBF, menggunakan satu item anchor.
- Preprocessing Sastrawi di-memoize saat refresh agar normalisasi teks lebih cepat.
- Support Apriori tetap pada angka absolut 3, dan dikonversi menjadi relative support pada setiap refresh.
- Normalisasi rating MCRS menggunakan skala tetap 1.0 sampai 5.0.

---

## Setup MCP Jupyter (untuk AI Coding Assistant)

Agar Antigravity (AGY) dan Claude Code dapat membaca dan menjalankan notebook secara langsung, `mcp-jupyter` perlu di-install dan dikonfigurasi sebagai MCP server yang terhubung ke JupyterLab lokal.

### 1. Instalasi Dependency

Dependency untuk tooling ini sudah didaftarkan di `requirements.txt` (bagian "MCP Jupyter tooling"), sehingga cukup jalankan:

```bash
pip install -r requirements.txt
```

Atau instalasi manual:

```bash
pip install jupyterlab mcp-jupyter "jupyter-kernel-client==0.15.0" "mcp==1.29.0"
```

> `jupyterlab` **wajib** ikut ter-install. `mcp-jupyter` tidak membawa `jupyterlab` sebagai dependency, sehingga tanpa itu, perintah `jupyter lab` akan gagal dengan error `Jupyter command 'jupyter-lab' not found`.

**Isu versi yang perlu diperhatikan:** `mcp-jupyter` mendeklarasikan beberapa dependency-nya tanpa batas atas versi, sehingga `pip install` polos dapat menarik versi terbaru yang breaking. Dua kasus yang sudah terjadi:

1. **`jupyter-kernel-client`** — `mcp-jupyter` bergantung pada `jupyter-kernel-client>=0.8.0`, sehingga pip dapat menarik versi terbaru (`1.0.0`) yang sudah me-rename class `KernelClient` menjadi `JupyterKernelClient`. Apabila hal ini terjadi, `mcp-jupyter` akan gagal start dengan error:

   ```
   ImportError: cannot import name 'KernelClient' from 'jupyter_kernel_client'
   ```

2. **`mcp`** — `mcp-jupyter` bergantung pada `mcp[cli]>=1.13.1`, sehingga pip dapat menarik versi terbaru (`2.0.0`) yang sudah me-rename modul `mcp.server.fastmcp` menjadi `mcp.server.mcpserver`. Apabila hal ini terjadi, `mcp-jupyter` akan gagal start dengan error:

   ```
   ModuleNotFoundError: No module named 'mcp.server.fastmcp'
   ```

Solusinya, pin kedua dependency tersebut ke versi lama yang masih kompatibel (nilai ini sudah ada di `requirements.txt`):

```bash
pip install "jupyter_kernel_client==0.15.0" "mcp==1.29.0"
```

Verifikasi cepat apakah kedua import sudah berjalan dengan benar:

```bash
python3 -c "from jupyter_kernel_client import KernelClient; print('OK')"
python3 -c "from mcp.server.fastmcp import FastMCP; print('OK')"
```

Atau verifikasi langsung dengan menjalankan server MCP-nya secara manual — kalau tidak ada traceback dan muncul log `Starting MCP server with stdio transport`, berarti sudah beres:

```bash
TOKEN=YOUR_TOKEN_HERE SERVER_URL=http://localhost:8888 python3 -m mcp_jupyter
```

### 2. Menjalankan JupyterLab

**Windows:**

```powershell
# start_jupyter.ps1
$TOKEN = "YOUR_TOKEN_HERE"
$PORT = 8888
jupyter lab --port $PORT --IdentityProvider.token $TOKEN --no-browser
```

**Ubuntu / Linux:**

```bash
# start_jupyter.sh
TOKEN="YOUR_TOKEN_HERE"
PORT=8888
jupyter lab --port $PORT --IdentityProvider.token=$TOKEN --no-browser
```

```bash
chmod +x start_jupyter.sh && ./start_jupyter.sh
```

Proses ini perlu dijalankan di terminal terpisah dan dibiarkan tetap hidup (tidak ditutup) selama akan digunakan melalui MCP — `mcp-jupyter` terhubung ke server yang sedang berjalan ini, bukan membuat proses baru.

`YOUR_TOKEN_HERE` perlu diganti dengan token acak yang aman sebelum digunakan secara aktual, dan placeholder ini tidak boleh dibiarkan di environment yang dapat diakses pihak lain.

### 3. Konfigurasi Antigravity (AGY)

Edit `~/.gemini/antigravity-cli/settings.json`, tambahkan blok `mcpServers`:

```json
{
  "mcpServers": {
    "jupyter": {
      "command": "python3",
      "args": ["-m", "mcp_jupyter"],
      "env": {
        "TOKEN": "YOUR_TOKEN_HERE",
        "SERVER_URL": "http://localhost:8888"
      }
    }
  }
}
```

> Windows: ganti `"python3"` dengan path absolut, misalnya `"C:/Program Files/Python311/python.exe"`.

Setelah diedit, **restart AGY**.

### 4. Konfigurasi Claude Code

Cara paling aman adalah melalui CLI `claude mcp`, agar file state internal `~/.claude.json` tidak diedit manual dan berisiko corrupt:

```bash
claude mcp add-json jupyter '{"command":"python3","args":["-m","mcp_jupyter"],"env":{"TOKEN":"YOUR_TOKEN_HERE","SERVER_URL":"http://localhost:8888"},"type":"stdio"}'
```

Perintah ini otomatis menambahkan entry ke `mcpServers` di dalam `projects["<path-project-ini>"]` pada `~/.claude.json`.

> Windows: ganti `"python3"` dengan `"C:/Program Files/Python311/python.exe"`.

Cara alternatif (edit manual): buka `~/.claude.json`, cari key `projects["<path-project>"]`, lalu tambahkan `mcpServers.jupyter` dengan isi JSON yang sama seperti di atas.

Setelah dikonfigurasi, **reload window VS Code** (`Ctrl+Shift+P` → *Developer: Reload Window*), atau restart sesi `claude` CLI.

### 5. Verifikasi Koneksi

```bash
claude mcp list
```

Apabila JupyterLab dari langkah 2 sedang berjalan dan token-nya sesuai, status yang tampil harus `✔ Connected`. Apabila muncul `✘ Failed to connect — Connection closed`, periksa dua hal berikut:

1. JupyterLab (`start_jupyter.sh` / `start_jupyter.ps1`) memang sedang berjalan di `localhost:8888`.
2. `TOKEN` pada konfigurasi MCP sama persis dengan `TOKEN` yang digunakan JupyterLab saat start.

### Mengganti Token

Apabila token perlu diganti, **3 tempat** berikut harus diperbarui secara konsisten:

| File | Lokasi |
|---|---|
| `start_jupyter.ps1` / `start_jupyter.sh` | Baris `TOKEN="..."` |
| AGY `settings.json` | `mcpServers.jupyter.env.TOKEN` |
| Claude Code | `mcpServers.jupyter.env.TOKEN` di `~/.claude.json`, atau jalankan ulang `claude mcp add-json` dengan token baru |
