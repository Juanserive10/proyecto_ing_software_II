import React, { useState } from 'react'
import { Plus, ShieldCheck } from 'lucide-react'
import { apiFetch } from '../api'
import { formatDate } from '../utils/format'
import Modal from './Modal'

export default function UsersView({ usersList, roles, onUpdated, notify }) {
  const [modalOpen, setModalOpen] = useState(false)
  const [form, setForm] = useState({ nombre: '', correo: '', contrasena: '', id_rol: 2 })

  const handleCreateUser = async (e) => {
    e.preventDefault()
    try {
      await apiFetch('usuarios', '/users', {
        method: 'POST',
        body: JSON.stringify({
          ...form,
          id_rol: Number(form.id_rol),
        }),
      })
      setForm({ nombre: '', correo: '', contrasena: '', id_rol: 2 })
      setModalOpen(false)
      await onUpdated()
      notify('Usuario creado correctamente')
    } catch (err) {
      notify(err.message, true)
    }
  }

  const handleRoleChange = async (u, nextRoleId) => {
    try {
      await apiFetch('usuarios', `/users/${u.id_usuario}`, {
        method: 'PUT',
        body: JSON.stringify({ id_rol: Number(nextRoleId) }),
      })
      await onUpdated()
      notify(`Rol actualizado para ${u.nombre}`)
    } catch (err) {
      notify(err.message, true)
    }
  }

  const handleToggleEstado = async (u) => {
    const next = u.estado === 'ACTIVO' ? 'INACTIVO' : 'ACTIVO'
    try {
      await apiFetch('usuarios', `/users/${u.id_usuario}`, {
        method: 'PUT',
        body: JSON.stringify({ estado: next }),
      })
      await onUpdated()
      notify(`Estado cambiado a ${next}`)
    } catch (err) {
      notify(err.message, true)
    }
  }

  return (
    <div className="view-enter">
      <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
        <button type="button" className="btn btn-sm" onClick={() => setModalOpen(true)}>
          <Plus size={14} /> Nuevo Usuario
        </button>
      </div>

      <section className="panel">
        <div className="panel-header">
          <div>
            <h3 className="panel-title">Usuarios y Control de Roles (RF07)</h3>
            <p className="panel-desc">Gestionados por el microservicio de Usuarios y Seguridad (JWT)</p>
          </div>
        </div>

        <div className="table-wrapper" role="region" aria-label="Usuarios del sistema" tabIndex={0}>
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Nombre</th>
                <th>Correo</th>
                <th>Rol Asignado</th>
                <th>Último Acceso</th>
                <th>Estado</th>
                <th>Acción</th>
              </tr>
            </thead>
            <tbody>
              {usersList.map((u) => (
                <tr key={u.id_usuario}>
                  <td className="mono">#{u.id_usuario}</td>
                  <td style={{ fontWeight: 600 }}>{u.nombre}</td>
                  <td>{u.correo}</td>
                  <td>
                    <select
                      aria-label={`Rol de ${u.nombre}`}
                      style={{ width: 'auto', padding: '0.3rem 0.55rem', fontSize: '0.8rem' }}
                      value={u.id_rol}
                      onChange={(e) => handleRoleChange(u, e.target.value)}
                    >
                      {roles.map((r) => (
                        <option key={r.id_rol} value={r.id_rol}>{r.nombre}</option>
                      ))}
                    </select>
                  </td>
                  <td style={{ fontSize: '0.78rem', color: 'var(--ink-muted)' }}>{formatDate(u.ultimo_acceso_en)}</td>
                  <td>
                    <span className={`badge ${u.estado === 'ACTIVO' ? 'badge-sage' : 'badge-neutral'}`}>
                      {u.estado}
                    </span>
                  </td>
                  <td>
                    <button type="button" className="btn btn-secondary btn-sm" onClick={() => handleToggleEstado(u)}>
                      {u.estado === 'ACTIVO' ? 'Desactivar' : 'Activar'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="panel">
        <div className="panel-header">
          <div>
            <h3 className="panel-title"><ShieldCheck size={16} /> Roles y Permisos Definidos</h3>
          </div>
        </div>
        <div className="grid-2">
          {roles.map((r) => (
            <div key={r.id_rol} style={{ border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', padding: '0.9rem' }}>
              <div style={{ fontWeight: 700, fontSize: '0.9rem' }}>{r.nombre}</div>
              <div style={{ fontSize: '0.8rem', color: 'var(--ink-muted)', margin: '0.25rem 0 0.55rem' }}>{r.descripcion}</div>
              <div style={{ display: 'flex', gap: '0.35rem', flexWrap: 'wrap' }}>
                {r.permisos.map((perm) => (
                  <span key={perm} className="badge badge-neutral mono">{perm}</span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="Registrar Nuevo Usuario">
        <form onSubmit={handleCreateUser} style={{ display: 'flex', flexDirection: 'column', gap: '0.9rem' }}>
          <div className="field">
            <label>Nombre completo</label>
            <input value={form.nombre} onChange={(e) => setForm({ ...form, nombre: e.target.value })} required />
          </div>
          <div className="field">
            <label>Correo electrónico</label>
            <input type="email" value={form.correo} onChange={(e) => setForm({ ...form, correo: e.target.value })} required />
          </div>
          <div className="form-grid">
            <div className="field">
              <label>Contraseña (mín. 6)</label>
              <input type="password" minLength={6} value={form.contrasena} onChange={(e) => setForm({ ...form, contrasena: e.target.value })} required />
            </div>
            <div className="field">
              <label>Rol</label>
              <select value={form.id_rol} onChange={(e) => setForm({ ...form, id_rol: e.target.value })}>
                {roles.map((r) => <option key={r.id_rol} value={r.id_rol}>{r.nombre}</option>)}
              </select>
            </div>
          </div>
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
            <button type="button" className="btn btn-secondary" onClick={() => setModalOpen(false)}>Cancelar</button>
            <button type="submit" className="btn">Crear Usuario</button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
