
# 🌿 LeafLens: AI Crop Disease Detector with a Multilingual Advice Assistant

> Snap a photo of a sick leaf. Get the disease, a visual explanation, a severity estimate, and treatment advice in **Telugu, Hindi or English**, by text or voice, even offline.

**100% free to build and host. Web app only (mobile-first PWA).**

---

## 1. Problem

Farmers often spot crop disease late and can't easily reach an agriculture officer. Existing apps mostly work in English, assume good internet, and give no reason for their predictions. LeafLens is a free, explainable, voice-friendly web app that works on a basic phone.

## 2. Features (all 12)

| # | Feature | What it does | Free tech |
|---|---------|--------------|-----------|
| 1 | **Disease detection (core)** | Upload or capture a leaf photo, get disease label + confidence | EfficientNet / ViT-small fine-tuned on PlantVillage + PlantDoc |
| 2 | **Multilingual LLM advice (core)** | Explains symptoms and treatment in Telugu / Hindi / English | Free-tier LLM API (Gemini or Groq) with fallback to a small open model |
| 3 | **Grad-CAM heatmap** | Shows which part of the leaf drove the prediction | `pytorch-grad-cam` |
| 4 | **"Not sure" handling** | Rejects non-leaf or low-confidence photos and asks for a better one | Softmax threshold + energy-based OOD score + leaf/non-leaf check |
| 5 | **Voice in and out** | Speak a question, hear the answer | Browser Web Speech API, `transformers.js` Whisper-tiny fallback, browser `speechSynthesis` |
| 6 | **Treatment RAG with citations** | Advice is grounded in real guidelines (ICAR, state agri dept PDFs) with source + page | FAISS/Chroma + `multilingual-e5-small` embeddings |
| 7 | **Chat-style mobile UI** *(replaces the Telegram bot)* | WhatsApp-like chat with big buttons, installable as a PWA | Plain HTML/JS or React + service worker |
| 8 | **Severity estimation** | "~30% of leaf area affected" to indicate urgency | Colour/lesion segmentation baseline, upgrade to a light U-Net |
| 9 | **Weather-aware advice** | Warns about fungal risk, spray timing, rain | Open-Meteo (no API key) |
| 10 | **Field diary** | Per-crop/plot scan history with trend (spreading vs recovering) | Browser IndexedDB (no server cost) |
| 11 | **Offline mode** | Run the model with no internet after first load | ONNX int8 + `onnxruntime-web` + service worker cache |
| 12 | **Feedback loop + outbreak map** | "Was this correct?" corrections for retraining, plus anonymous district-level hotspot map | Supabase free tier + Leaflet + OpenStreetMap |

> **Note on the Telegram bot:** since this project is web-only, the bot is replaced by a chat-style, installable PWA, which gives the same "farmers already use chat apps" experience with no extra platform.

## 3. Zero-cost stack

| Layer | Choice | Cost |
|-------|--------|------|
| Model training | Google Colab / Kaggle free GPU | Free |
| Model hosting + backend | Hugging Face Spaces (free CPU, Docker + FastAPI) | Free |
| Frontend | Static files served by FastAPI (or Vercel / Netlify / GitHub Pages) | Free |
| LLM | Gemini or Groq free tier (check current limits) | Free |
| Embeddings / RAG | `multilingual-e5-small` on CPU, prebuilt index committed to repo | Free |
| Speech | Browser Web Speech API + `transformers.js` | Free |
| Weather | Open-Meteo | Free |
| Shared data (feedback, map) | Supabase free tier | Free |
| Maps | Leaflet + OpenStreetMap | Free |
| Code hosting + CI | GitHub + GitHub Actions | Free |

Free tiers have rate limits, so the app caches LLM answers and degrades gracefully when a quota is hit.

## 4. Architecture

```
┌──────────────────────── Browser (PWA) ─────────────────────────┐
│ Chat UI · camera/upload · voice (STT/TTS) · IndexedDB diary      │
│ onnxruntime-web (offline model) · service worker cache           │
└───────────────┬──────────────────────────────────────────────────┘
                │ HTTPS
┌───────────────▼──────────── FastAPI (HF Space) ──────────────────┐
│ /predict   → ONNX model → label, confidence, OOD flag, Grad-CAM  │
│ /severity  → segmentation → % area affected                      │
│ /advice    → RAG (FAISS) + weather + LLM → answer + citations    │
│ /feedback  → Supabase (corrections)                              │
│ /outbreaks → Supabase (aggregated, district-level)               │
└───────┬───────────────┬───────────────┬──────────────────────────┘
        │               │               │
   Open-Meteo      Free LLM API     Supabase (free)
```

**Request flow:** photo → OOD check → classify → Grad-CAM + severity → fetch weather → retrieve guideline chunks → LLM writes advice in the user's language with citations → UI shows result, speaks it if voice is on → scan saved to the local diary.

## 5. Project structure

```
leaflens/
├── README.md
├── PROMPTS.md                 # prompts that worked (vibe-coding log)
├── requirements.txt
├── notebooks/
│   ├── 01_train_classifier.ipynb
│   ├── 02_ood_and_robustness.ipynb     # PlantVillage vs PlantDoc gap
│   ├── 03_severity_segmentation.ipynb
│   └── 04_export_onnx_int8.ipynb
├── backend/
│   ├── main.py                # FastAPI app
│   ├── model.py               # ONNX inference + OOD
│   ├── gradcam.py
│   ├── severity.py
│   ├── rag.py                 # FAISS index + retrieval
│   ├── advice.py              # prompt building + LLM call + cache
│   ├── weather.py             # Open-Meteo client
│   └── db.py                  # Supabase client
├── data/
│   ├── guidelines/            # source PDFs (ICAR, state agri depts)
│   └── index/                 # prebuilt FAISS index
├── frontend/
│   ├── index.html
│   ├── app.js
│   ├── sw.js                  # service worker (offline)
│   ├── manifest.json
│   └── models/                # ONNX model for offline use
├── tests/
└── Dockerfile
```

## 6. Getting started

```bash
git clone https://github.com/<you>/leaflens.git
cd leaflens
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# environment variables (all free keys)
export LLM_API_KEY=...          # Gemini or Groq free key
export SUPABASE_URL=...
export SUPABASE_KEY=...

uvicorn backend.main:app --reload
# open http://localhost:8000
```

**Train the model:** open `notebooks/01_train_classifier.ipynb` in Colab (free GPU), run all cells, then export with notebook 04 and place the `.onnx` file in `backend/` and `frontend/models/`.

**Build the RAG index:** drop guideline PDFs into `data/guidelines/` and run `python -m backend.rag --build`.

## 7. Datasets

- **PlantVillage**: clean lab-style leaf images, good for a baseline
- **PlantDoc**: real-field images, used to measure and reduce the lab-to-field accuracy gap
- **Guideline PDFs**: public ICAR and state agriculture department documents (verify licensing before redistributing; keep links instead of copies if unsure)

## 8. Evaluation (what makes this portfolio-grade)

Report all of these in the repo:

- Accuracy, macro-F1 and a confusion matrix on PlantVillage
- **Accuracy on PlantDoc without and with field augmentation** (the robustness gap)
- OOD detection: AUROC for leaf vs non-leaf and unseen-disease images
- Severity: error against a small hand-labelled set
- RAG: retrieval hit-rate and a manual faithfulness check on 30 questions
- Translation quality: Telugu/Hindi output reviewed by a native speaker
- Offline model: size, int8 accuracy drop, latency on a mid-range phone
- A **failure cases** section with real examples

## 9. Milestones

| Week | Goal |
|------|------|
| 1 | Baseline classifier in Colab, deploy a bare FastAPI + upload page to HF Spaces |
| 2 | Grad-CAM, OOD "not sure" logic, PlantDoc robustness work |
| 3 | LLM advice in 3 languages, RAG with citations |
| 4 | Chat PWA UI, voice in/out, field diary |
| 5 | Severity estimation, weather-aware advice |
| 6 | ONNX offline mode, feedback + outbreak map |
| 7 | Evaluation write-up, demo video, polish |

## 10. Team split (if collaborating)

- **ML:** training, robustness, Grad-CAM, OOD, severity, ONNX export
- **Backend/AI:** FastAPI, RAG, LLM prompts, weather, Supabase
- **Frontend:** PWA UI, voice, diary, offline caching, map, deployment, demo

Work on feature branches, open small PRs, and make the author explain each AI-generated diff before merging.

## 11. Vibe-coding workflow

1. Keep this README as the spec and reference it in every prompt.
2. Log successful prompts in `PROMPTS.md`.
3. Ask the AI to write tests, then run them yourself.
4. Review every change you can't explain. You should be able to defend each module in an interview.
5. Deploy early and iterate on the live link.

## 12. Privacy

- Photos are processed for prediction and are **not stored** unless the user opts in to share them for retraining.
- The outbreak map uses **district-level** location only, never exact coordinates.
- The field diary lives in the user's own browser.

## 13. ⚠️ Disclaimer

LeafLens gives informational guidance, not professional agronomic advice. Pesticide choice and dosage must be confirmed with a local agriculture officer or the product label. The app always shows this notice next to chemical treatment suggestions, and prefers organic and cultural controls where effective.

## 14. Known limitations

- Models trained on lab images lose accuracy on messy field photos.
- Only crops/diseases present in the training data are supported.
- Free LLM and hosting tiers have rate limits and cold starts.
- Browser voice support for Telugu varies by device.
- Whisper-tiny is weak for Telugu, so the browser speech API is the primary path.

## 15. Roadmap

- More crops and regional diseases (rice, chilli, cotton)
- Pest (insect) detection
- Crowd-labelled field dataset from user feedback
- Fully on-device LLM for advice

## 16. License

MIT for code. Check each dataset's and document's own license before reuse.

## 17. Acknowledgements

PlantVillage and PlantDoc dataset authors, Hugging Face, Open-Meteo, OpenStreetMap, ICAR and state agriculture departments.
