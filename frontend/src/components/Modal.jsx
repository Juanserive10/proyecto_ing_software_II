import React, { useEffect, useId, useRef } from 'react'
import { X } from 'lucide-react'

export default function Modal({ open, onClose, title, children }) {
  const dialogRef = useRef(null)
  const titleId = useId()

  useEffect(() => {
    const el = dialogRef.current
    if (!el) return
    if (open && !el.open) {
      el.showModal()
    } else if (!open && el.open) {
      el.close()
    }
  }, [open])

  const handleCancel = (e) => {
    e.preventDefault()
    onClose?.()
  }

  const handleBackdropPointer = (e) => {
    const el = dialogRef.current
    if (!el) return
    const rect = el.getBoundingClientRect()
    const outside =
      e.clientX < rect.left ||
      e.clientX > rect.right ||
      e.clientY < rect.top ||
      e.clientY > rect.bottom
    if (outside) {
      onClose?.()
    }
  }

  return (
    <dialog
      ref={dialogRef}
      className="app-dialog"
      aria-labelledby={titleId}
      onCancel={handleCancel}
      onClick={handleBackdropPointer}
    >
      <div className="dialog-head">
        <h3 id={titleId} style={{ fontSize: '1.05rem' }}>{title}</h3>
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          onClick={onClose}
          aria-label="Cerrar ventana"
        >
          <X size={15} />
        </button>
      </div>
      <div className="dialog-body">{children}</div>
    </dialog>
  )
}
