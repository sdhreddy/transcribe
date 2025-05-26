import { useState, useRef, useEffect } from 'react'
import './App.css'

function App() {
  const [recording, setRecording] = useState(false)
  const [transcript, setTranscript] = useState('')
  const [message, setMessage] = useState('')
  const [chat, setChat] = useState([])
  const [models, setModels] = useState([])
  const [model, setModel] = useState('base')
  const recorderRef = useRef(null)
  const chunksRef = useRef([])

  useEffect(() => {
    fetch('/api/models')
      .then(r => r.json())
      .then(d => {
        setModels(d.models)
        if (d.models?.length) setModel(d.models[0])
      })
    fetch('/api/settings/model')
      .then(r => r.json())
      .then(d => setModel(d.value))
      .catch(() => {})
  }, [])

  const startRecording = async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    const rec = new MediaRecorder(stream)
    rec.ondataavailable = e => {
      if (e.data.size > 0) chunksRef.current.push(e.data)
    }
    rec.onstop = async () => {
      const blob = new Blob(chunksRef.current, { type: 'audio/webm' })
      chunksRef.current = []
      const fd = new FormData()
      fd.append('file', blob, 'recording.webm')
      fd.append('model', model)
      const resp = await fetch('/api/transcribe', { method: 'POST', body: fd })
      const data = await resp.json()
      setTranscript(t => t + '\n' + data.text)
    }
    recorderRef.current = rec
    rec.start()
    setRecording(true)
  }

  const stopRecording = () => {
    recorderRef.current.stop()
    setRecording(false)
  }

  const playTTS = async text => {
    const fd = new FormData()
    fd.append('text', text)
    const resp = await fetch('/api/tts', { method: 'POST', body: fd })
    const blob = await resp.blob()
    new Audio(URL.createObjectURL(blob)).play()
  }

  const sendChat = async () => {
    const fd = new FormData()
    fd.append('message', message)
    const resp = await fetch('/api/chat', { method: 'POST', body: fd })
    const data = await resp.json()
    setChat(c => [...c, { role: 'user', text: message }, { role: 'assistant', text: data.text }])
    setMessage('')
    playTTS(data.text)
  }

  const changeModel = async val => {
    setModel(val)
    const resp = await fetch(`/api/settings/model?value=${val}`, { method: 'POST' })
    if (!resp.ok) console.error('Failed to save setting')
  }

  return (
    <div className="container">
      <h1>Transcribe Web</h1>
      <div className="controls">
        {recording ? (
          <button onClick={stopRecording}>Stop</button>
        ) : (
          <button onClick={startRecording}>Record</button>
        )}
        <select value={model} onChange={e => changeModel(e.target.value)}>
          {models.map(m => (
            <option key={m} value={m}>{m}</option>
          ))}
        </select>
      </div>
      <textarea readOnly value={transcript} rows="6" className="transcript" />
      <div className="chat-box">
        {chat.map((c, i) => (
          <div key={i} className={c.role}>{c.text}</div>
        ))}
        <div className="chat-input">
          <input value={message} onChange={e => setMessage(e.target.value)} placeholder="Say something" />
          <button onClick={sendChat}>Send</button>
        </div>
      </div>
    </div>
  )
}

export default App
