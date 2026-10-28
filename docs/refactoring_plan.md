# Rencana Refactoring: Type Safety (Zero `Any`), Batasan Parameter, Urutan Method, & Go Guidelines (Revisi v2)

Dokumen ini memuat analisis mendalam, pemetaan komponen terdampak, serta rencana langkah implementasi refactoring untuk repositori `artour-recommender` berdasarkan arsitektur Clean Architecture Temas (`shipping-be`) dan kaidah Go Guidelines.

---

## 1. Latar Belakang & Prinsip Utama

Refactoring ini bertujuan untuk meningkatkan keandalan, keterbacaan, dan konsistensi kode microservice `artour-recommender` agar selaras dengan standar arsitektur backend Temas (sebagaimana diterapkan pada `shipping-be` dan panduan Go Coding Guidelines `~/.gemini/config/coding-guidelines-go.md`).

### 5 Pilar Utama Refactoring:
1. **Zero `Any` (Exact Typing Tanpa Dummy Protocol)**:
   - Hindari semua penggunaan tipe `Any`.
   - Gunakan concrete types (`pd.DataFrame`, `pd.Series`, `scipy.sparse.csr_matrix`, `dict[str, object]`, dll.).
   - Untuk Sastrawi Stemmer, gunakan class konkret `CachedStemmer` langsung dari `Sastrawi.Stemmer.CachedStemmer`, **bukan** membuat dummy `StemmerProtocol(Protocol)` dengan method `...` (elipsis) yang janggal pada kode aplikasi.
2. **Maksimal 3 Parameter per Method / Fungsi**:
   - Selaras dengan Bagian 1 Go Coding Guidelines: setiap method/fungsi bisnis operasional hanya boleh menerima maksimal 3 parameter.
   - Pengecualian mutlak: Constructor (`__init__`).
   - Jika parameter $\ge 4$, bungkus argumen ke dalam dataclass DTO (misal struct parameter di `src/entity/recommendation.py`).
3. **Urutan Method dalam Class yang Terstruktur**:
   - Constructor (`__init__`) di paling atas.
   - **Public methods** (termasuk `@property`) diletakkan terlebih dahulu.
   - **Protected methods** (diawali satu underscore `_`) setelah public methods.
   - **Private methods** (diawali double underscore `__`) di paling bawah.
4. **Pemisahan Boundary Entity vs Presenter vs Client (Clean Architecture)**:
   - **`src/entity/`**: Murni untuk entitas data internal bisnis (seperti `DataBundle`, internal parameter tuning). Tidak boleh tercampur dengan schema JSON HTTP luar.
   - **`src/adapter/presenter/`**: Presenter layer untuk respons HTTP keluar ke client REST, menggunakan sufiks `*Output` (contoh: `UserToItemOutput`, `HealthOutput`). DTO input dari user menggunakan sufiks `*Input` (contoh: `UserToItemInput`, `RefreshTriggerInput`).
   - **`src/clients/entity/`**: Model kontrak untuk komunikasi HTTP ke service eksternal (NestJS). Payload yang dikirim ke luar dinamai `*Request` (contoh: `RefreshWebhookRequest`).
5. **Penamaan File Berbasis Kata Benda (Noun-based Naming)**:
   - Mengikuti konvensi Go (`pkg/entity/recommendation.go`, `pkg/adapter/presenter/recommendation.go`, `pkg/adapter/presenter/admin.go`, `pkg/clients/entity/webhook.go`).
   - Hindari sufiks file yang redundan seperti `model_dto.py`, `admin_dto.py`, atau `recommendation_dto.py`. Gunakan kata benda domain murni: `recommendation.py`, `admin.py`, `webhook.py`.

---

## 2. Struktur Direktori Target

```
src/
├── entity/                           # MURNI domain internal bisnis & parameter algoritma
│   ├── __init__.py
│   └── recommendation.py             # DataBundle, AprioriFitParams, CBFRankParams, MCRSRankParams, CascadePaddingParams
│
├── clients/
│   ├── __init__.py
│   ├── webhook_client.py             # HTTP client ke NestJS
│   └── entity/                       # Model kontrak keluar ke eksternal service
│       ├── __init__.py
│       └── webhook.py                # RefreshWebhookRequest
│
└── adapter/
    ├── handlers/                     # Controller / Route handlers
    │   ├── __init__.py
    │   ├── admin_handler.py
    │   ├── dependencies.py
    │   ├── health_handler.py
    │   └── recommendation_handler.py
    ├── presenter/                    # Schema presentasi REST API (Input & Output)
    │   ├── __init__.py
    │   ├── response.py               # JSONResponse helper
    │   ├── admin.py                  # HealthOutput, RefreshOutput, RefreshAcceptedOutput, RefreshTriggerInput, Envelopes
    │   └── recommendation.py         # BaseOutput, UserToItemOutput, ItemToItemOutput, RecommendationItemOutput, Explanations, UserToItemInput
    └── routes/
        ├── __init__.py
        └── router.py
```

---

## 3. Rencana Perubahan Detail per Komponen

### A. Algoritma: `src/module/recommendation/algorithms/text_preprocessor.py`
- **Isu**: Deklarasi `class StemmerProtocol(Protocol): def stem(self, text: str) -> str: ...` terlihat aneh dan tidak wajar di production code.
- **Solusi**:
  1. Hapus `StemmerProtocol`.
  2. Import langsung class konkret dari Sastrawi:
     ```python
     from Sastrawi.Stemmer.CachedStemmer import CachedStemmer
     ```
  3. Ketik variabel global dan instance secara konkret:
     ```python
     _PROCESS_STEMMER: CachedStemmer | None = None
     ...
     self._stemmer: CachedStemmer = cast(CachedStemmer, StemmerFactory().create_stemmer())
     ```
  4. Urutan method: `__init__` $\rightarrow$ public `preprocess_places` $\rightarrow$ protected `_clean_text`, `_stem_word`, `_parallel_stem_unknown_words`.

### B. Domain Internal: `src/entity/recommendation.py` (Rename dari `model_dto.py`)
- **Isu**: Nama file `model_dto.py` tidak mencerminkan kata benda domain, dan `src/entity/` masih tercampur DTO response HTTP (`admin_dto.py`, `recommendation_dto.py`).
- **Solusi**:
  1. Hapus `src/entity/admin_dto.py` dan `src/entity/recommendation_dto.py`.
  2. Rename `src/entity/model_dto.py` $\rightarrow$ `src/entity/recommendation.py`.
  3. Isi `src/entity/recommendation.py` murni entitas internal:
     - `DataBundle`:
       ```python
       @dataclass(frozen=True)
       class DataBundle:
           places: pd.DataFrame
           interactions: pd.DataFrame
       ```
     - Dataclass parameter pembungkus (maksimal 3 parameter per method):
       ```python
       @dataclass(frozen=True)
       class AprioriFitParams:
           absolute_support: int = 3
           max_len: int = 3
           min_user_interactions: int = 2

       @dataclass(frozen=True)
       class CBFRankParams:
           exclude_ids: set[str]
           needed: int
           source: str

       @dataclass(frozen=True)
       class MCRSRankParams:
           place_lookup: Mapping[str, dict[str, float]]
           min_price: float
           max_price: float
           limit: int

       @dataclass(frozen=True)
       class CascadePaddingParams:
           padding_candidates: list[dict[str, object]]
           target_n: int
           padding_source: str
       ```

### C. Client Outgoing DTO: `src/clients/entity/webhook.py`
- **Isu**: `RefreshWebhookPayload` adalah payload yang dikirim keluar oleh microservice recommender ke NestJS via HTTP POST, sehingga konsepnya adalah outgoing request.
- **Solusi**:
  1. Buat folder baru `src/clients/entity/`.
  2. Buat file `src/clients/entity/webhook.py`.
  3. Ubah nama class menjadi `RefreshWebhookRequest`:
     ```python
     class RefreshWebhookRequest(BaseModel):
         model_config = ConfigDict(populate_by_name=True)

         refresh_id: str = Field(validation_alias=AliasChoices("refresh_id", "refreshId"), serialization_alias="refreshId")
         status: Literal["success", "failed"]
         finished_at: datetime = Field(validation_alias=AliasChoices("finished_at", "finishedAt"), serialization_alias="finishedAt")
         places_count: int | None = Field(default=None, validation_alias=AliasChoices("places_count", "placesCount"), serialization_alias="placesCount")
         interactions_count: int | None = Field(default=None, validation_alias=AliasChoices("interactions_count", "interactionsCount"), serialization_alias="interactionsCount")
         error: str | None = None
     ```

### D. Presenter REST API: `src/adapter/presenter/`
- **Isu**: Seluruh response yang dikirim ke client luar sebelumnya berada di `src/entity/` dan dinamai `*Response`.
- **Solusi**:
  1. **`src/adapter/presenter/admin.py`**:
     - `RefreshTriggerInput` (menggantikan `RefreshTriggerRequest` sebagai input request ke `/refresh`).
     - `HealthOutput` (menggantikan `HealthResponse`).
     - `RefreshOutput` (menggantikan `RefreshResponse`).
     - `RefreshAcceptedOutput` (menggantikan `RefreshAcceptedResponse`).
     - `RefreshEnvelopeOutput = BaseOutput[RefreshOutput]`.
     - `RefreshAcceptedEnvelopeOutput = BaseOutput[RefreshAcceptedOutput]`.
  2. **`src/adapter/presenter/recommendation.py`**:
     - `BaseOutput[T]` (menggantikan `BaseResponse`).
     - `UserToItemInput` (menggantikan `UserToItemRequest`).
     - `AprioriExplanation`, `CbfExplanation`, `McrsExplanation`, `RecommendationExplanation`.
     - `RecommendationItemOutput` (menggantikan `RecommendationItemResponse`).
     - `UserToItemOutput` (menggantikan `UserToItemRecommendationResponse`).
     - `ItemToItemOutput` (menggantikan `ItemToItemRecommendationResponse`).
     - `UserToItemEnvelopeOutput = BaseOutput[UserToItemOutput]`.
     - `ItemToItemEnvelopeOutput = BaseOutput[ItemToItemOutput]`.
  3. **`src/adapter/presenter/response.py`**:
     - `build_success_response(data: object, ...)` (menggunakan tipe `object`, 0 `Any`).

### E. Penyelarasan Consumer Code (Handlers, Services, Jobs, Tests)
1. **`src/adapter/handlers/admin_handler.py`**:
   - Signature handler `/refresh`:
     ```python
     @router.post(
         "/refresh",
         response_model=RefreshAcceptedEnvelopeOutput,
         status_code=status.HTTP_202_ACCEPTED,
         dependencies=[Depends(verify_refresh_token)],
     )
     async def refresh(
         background_tasks: BackgroundTasks,
         payload: RefreshTriggerInput | None = Body(default=None),
         deps: AdminDependencies = Depends(get_admin_dependencies),
     ) -> RefreshAcceptedEnvelopeOutput:
     ```
   - Total parameter: **3 parameter** (memenuhi batas maksimal 3 parameter).
2. **`src/adapter/handlers/recommendation_handler.py`**:
   - Menggunakan `UserToItemEnvelopeOutput`, `ItemToItemEnvelopeOutput`, `UserToItemInput`.
   - Menggunakan `AprioriExplanation.from_dict(...)` (0 `Any`).
3. **`src/clients/webhook_client.py` & `src/module/recommendation/refresh_job.py`**:
   - Menggunakan `RefreshWebhookRequest` dari `src.clients.entity.webhook`.
4. **`tests/`**:
   - Mengupdate import di `tests/test_api_smoke.py`, `tests/test_recommendation_service.py`, `tests/test_src_architecture.py` agar mengarah ke `src.entity.recommendation` dan `src.adapter.presenter.*`.

---

## 4. Matriks Pemetaan Nama Lama vs Nama Baru

| Lokasi Lama | Nama Lama | Lokasi Baru | Nama Baru | Kategori Arsitektur |
| :--- | :--- | :--- | :--- | :--- |
| `src/entity/admin_dto.py` | `HealthResponse` | `src/adapter/presenter/admin.py` | `HealthOutput` | Presenter Output |
| `src/entity/admin_dto.py` | `RefreshResponse` | `src/adapter/presenter/admin.py` | `RefreshOutput` | Presenter Output |
| `src/entity/admin_dto.py` | `RefreshAcceptedResponse` | `src/adapter/presenter/admin.py` | `RefreshAcceptedOutput` | Presenter Output |
| `src/entity/admin_dto.py` | `RefreshEnvelope` | `src/adapter/presenter/admin.py` | `RefreshEnvelopeOutput` | Presenter Output |
| `src/entity/admin_dto.py` | `RefreshAcceptedEnvelope` | `src/adapter/presenter/admin.py` | `RefreshAcceptedEnvelopeOutput` | Presenter Output |
| `src/entity/admin_dto.py` | `RefreshTriggerRequest` | `src/adapter/presenter/admin.py` | `RefreshTriggerInput` | Presenter/Handler Input |
| `src/entity/admin_dto.py` | `RefreshWebhookPayload` | `src/clients/entity/webhook.py` | `RefreshWebhookRequest` | Client Outgoing Request |
| `src/entity/recommendation_dto.py` | `BaseResponse` | `src/adapter/presenter/recommendation.py` | `BaseOutput` | Presenter Output Envelope |
| `src/entity/recommendation_dto.py` | `UserToItemRecommendationResponse` | `src/adapter/presenter/recommendation.py` | `UserToItemOutput` | Presenter Output |
| `src/entity/recommendation_dto.py` | `ItemToItemRecommendationResponse` | `src/adapter/presenter/recommendation.py` | `ItemToItemOutput` | Presenter Output |
| `src/entity/recommendation_dto.py` | `RecommendationItemResponse` | `src/adapter/presenter/recommendation.py` | `RecommendationItemOutput` | Presenter Output |
| `src/entity/recommendation_dto.py` | `UserToItemRequest` | `src/adapter/presenter/recommendation.py` | `UserToItemInput` | Presenter/Handler Input |
| `src/entity/model_dto.py` | `DataBundle`, Params | `src/entity/recommendation.py` | `DataBundle`, Params | Pure Domain Entity |

---

## 5. Rencana Langkah Eksekusi (Next Actions)

1. **Langkah 1**: Buat package `src/clients/entity/` dan file `webhook.py` (`RefreshWebhookRequest`).
2. **Langkah 2**: Buat presenter `src/adapter/presenter/recommendation.py` dan `src/adapter/presenter/admin.py`.
3. **Langkah 3**: Buat domain internal `src/entity/recommendation.py` dan hapus `model_dto.py`, `admin_dto.py`, `recommendation_dto.py`.
4. **Langkah 4**: Refactor `text_preprocessor.py` untuk menggunakan `CachedStemmer` langsung tanpa `StemmerProtocol`.
5. **Langkah 5**: Update import dan wiring pada `handlers/`, `webhook_client.py`, `refresh_job.py`, `service.py`, `repository.py`, dan seluruh unit test.
6. **Langkah 6**: Verifikasi statis Pyright (0 errors) dan jalankan Pytest (8/8 passed).
7. **Langkah 7**: Update learning diary.
