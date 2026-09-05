# 🤖 AI Projects

A collection of practical Artificial Intelligence and full-stack projects focused on solving real-world problems.

## 📁 Projects

| Project | Description | Technologies | Status |
|---|---|---|---|
| [NeuraVault](./neuravault) | AI-powered workspace for interacting with documents and storing knowledge. | Next.js, React, TypeScript, Clerk, Neon, Groq | 🚧 In Development |
| [SignBridge](./signbridge) | Accessibility platform that converts sign language into text/speech and speech into text. | Python, MediaPipe, PyTorch, FastAPI, React | 🚧 In Development |

---

## 🧠 NeuraVault

NeuraVault is an AI-powered knowledge workspace where users can upload documents, interact with their content, generate answers, and save useful information.

### Features

- User authentication
- Document upload and processing
- AI-powered document interaction
- Persistent database storage
- Markdown and mathematical content rendering
- Responsive Next.js interface

---

## 🤟 SignBridge

SignBridge is an accessibility platform designed to reduce the communication gap between sign-language users and spoken-language users.

### System Workflow

1. Capture sign language using a camera.
2. Extract hand and body landmarks.
3. Convert frames into fixed-length sequences.
4. Classify signs using a deep-learning model.
5. Convert predicted signs into readable text.
6. Generate speech from the recognized text.
7. Convert spoken language into text.

### Main Modules

- **Vision:** Hand and pose landmark extraction
- **Training:** Dataset preprocessing and model training
- **Inference:** Real-time sign prediction
- **Audio:** Speech-to-text and text-to-speech
- **Language:** Text processing and sentence generation
- **Backend:** FastAPI endpoints
- **Frontend:** Camera and conversation interface

---

## 🗂️ Repository Structure

```text
AI-Projects/
├── neuravault/    # AI knowledge and document workspace
└── signbridge/    # Sign-language communication platform
```

## 🚀 Getting Started

Clone the repository:

```bash
git clone https://github.com/vamsi54-bit/AI-Projects.git
cd AI-Projects
```

Open NeuraVault:

```bash
cd neuravault
```

Or open SignBridge:

```bash
cd signbridge
```

Each project contains its own dependencies and setup process.

## 🤝 Contributing

1. Fork this repository.
2. Create a new branch.
3. Make and test your changes.
4. Commit your changes.
5. Open a pull request.

## 👨‍💻 Author

Created and maintained by [Vamsi](https://github.com/vamsi54-bit).
