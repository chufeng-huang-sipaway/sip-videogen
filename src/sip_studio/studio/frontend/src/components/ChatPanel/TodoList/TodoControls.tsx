//TodoControls component - pause/resume/stop/new direction buttons
import{useState}from'react'
import'./TodoList.css'
interface TodoControlsProps{
  isPaused:boolean
  onPause:()=>void
  onResume:()=>void
  onStop:()=>void
  onNewDirection:(msg:string)=>void
}
export function TodoControls({isPaused,onPause,onResume,onStop,onNewDirection}:TodoControlsProps){
  const[showDir,setShowDir]=useState(false)
  const[dirMsg,setDirMsg]=useState('')
  const handleSend=()=>{if(dirMsg.trim()){onNewDirection(dirMsg);setShowDir(false);setDirMsg('')}}
  return(
    <div className="todo-controls">
      {isPaused?(
        <button className="todo-btn todo-btn--resume" onClick={onResume}>Resume</button>
      ):(
        <button className="todo-btn todo-btn--pause" onClick={onPause} title="Pauses after current step">Pause</button>
      )}
      <button className="todo-btn todo-btn--stop" onClick={onStop} title="Stops after current step">Stop</button>
      <button className="todo-btn todo-btn--direction" onClick={()=>setShowDir(true)}>New Direction</button>
      {showDir&&(
        <div className="new-direction-input">
          <input value={dirMsg} onChange={e=>setDirMsg(e.target.value)} placeholder="New instructions..." className="direction-input"/>
          <button className="todo-btn todo-btn--send" onClick={handleSend}>Send</button>
          <button className="todo-btn todo-btn--cancel" onClick={()=>setShowDir(false)}>Cancel</button>
        </div>
      )}
      <p className="todo-hint">Actions take effect after the current step completes</p>
    </div>
  )
}
