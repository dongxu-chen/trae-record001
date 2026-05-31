import React from 'react'

function Toast({ message, type = 'info' }) {
  return (
    <div className="toast">
      {message}
    </div>
  )
}

export default Toast
