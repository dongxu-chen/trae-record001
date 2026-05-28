import { HandwritingRecognition } from './components/HandwritingRecognition'
import './App.css'

function App() {
  return (
    <main className="app">
      <header className="app__header">
        <h1>✍️ Web 手写识别</h1>
        <p className="app__sub">
          Canvas + TensorFlow.js + React + WebWorker · 支持汉字、数字、字母，连续书写、笔迹平滑与低延迟识别。
        </p>
      </header>

      <section className="app__body">
        <HandwritingRecognition width={720} height={260} topK={6} />
      </section>

      <footer className="app__footer">
        <small>在下方区域用手指或鼠标书写，可连续书写多字，系统会自动分段并给出候选字。</small>
      </footer>
    </main>
  )
}

export default App
