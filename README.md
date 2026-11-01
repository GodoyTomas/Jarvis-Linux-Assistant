# 🤖 Jarvis — Asistente de Voz e Investigación para Hardware Ligero (Linux)

Asistente virtual controlado por voz inspirado en **Jarvis (Iron Man)**, diseñado y optimizado específicamente para ejecutarse con un consumo mínimo de memoria RAM (< 80 MB) en distribuciones ligeras como **Lubuntu 24.04 LTS** y procesadores clásicos sin instrucciones AVX (como notebooks **HP 420 Dual-Core**).

## 🚀 Características Principales

- **Detección Acústica de Doble Umbral (Zero-AVX):** Captura de voz mediante módulos nativos (`audioop` y `wave`) con calibración automática de ruido ambiente al iniciar, evitando bloqueos de arquitectura (`Illegal instruction`) en CPUs antiguas y filtrando conversaciones lejanas.
- **Transcripción Neuronal en Alta Definición:** Integración directa con **Whisper Large V3 Turbo** para comprender consultas técnicas extensas con pausas naturales de hasta 2.2 segundos.
- **Cerebro Multi-Motor con Failover Automático:** Rotación inteligente entre modelos de alto rendimiento (`openai/gpt-oss-120b`, `qwen/qwen3.8-27b` y `openai/gpt-oss-20b`) para garantizar disponibilidad continua sin agotar cuotas.
- **Investigación Web en Tiempo Real y Generación de Informes:** Búsqueda en vivo en la web, noticias y Wikipedia. Al solicitar una investigación, Jarvis redacta un informe técnico en formato Markdown (`.md`) en `~/Documentos/Investigaciones_Jarvis` y pronuncia una síntesis ejecutiva.
- **Síntesis de Voz con Ecualización Acústica:** Timbre personalizado mediante `edge-tts` y procesamiento de filtros `lavfi` en `mpv`.

## 🛠️ Requisitos del Sistema (Linux)

```bash
sudo apt update && sudo apt install -y python3-venv python3-full libportaudio2 libportaudiocpp0 portaudio19-dev mpv alsa-utils
