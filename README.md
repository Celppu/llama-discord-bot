# 🦙 Llama-Discord-Bot

A Discord bot utilizing Llama models in GGML format.

## 📋 Prerequisites

Before you begin, ensure you have met the following requirements:

- You have installed WSL 2
- You have installed the Nvidia Toolkit
- You have added the Nvidia compiler to your cmake environment variables

## 🛠 Installation

Follow these steps to get your Discord bot up and running:

1. Install Llama with CuBLAS using pip install as per instructions given in the [Llama CPP Python](https://github.com/abetlen/llama-cpp-python) repository.

### Setup Environment Variables

Create a `.env` file at the root of your project and add your Discord token and model path:

```bash
DISCORD_TOKEN=your-token
MODEL_PATH=path-to-your-model
```

The current version of LLAMA_CPP requires the following environment variable due to a bug in WSL for pinned memory:

```bash
GGML_CUDA_NO_PINNED=1
```

## 👩‍💻 Usage

Now you're ready to go! Enjoy using your Llama-based Discord bot.

## 📝 Note 

Remember that this project is under construction, there might be constant changes and updates, so stay tuned!

## 👥 Contributing

If you'd like to contribute, please fork the repository and use a feature branch. Pull requests are warmly welcome.

## 📧 Contact

If you have any questions or issues, please open an issue here or reach out to the author.
