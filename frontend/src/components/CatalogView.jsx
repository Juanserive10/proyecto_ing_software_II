import React, { useMemo, useState } from 'react'
import { Download, Edit3, Plus, Search, Upload } from 'lucide-react'
import { apiFetch } from '../api'
import { downloadCsv, formatMoney } from '../utils/format'
import Modal from './Modal'

export default function CatalogView({ user, products, categories, stocks, onUpdated, notify }) {
  const canManage = user?.rol === 'ADMINISTRADOR'
  const [subTab, setSubTab] = useState('productos') // 'productos' | 'categorias' | 'importar'
  const [searchQ, setSearchQ] = useState('')
  const [filterCat, setFilterCat] = useState('ALL')

  const [prodModal, setProdModal] = useState(null) // null | { mode: 'create' | 'edit', data }
  const [catModal, setCatModal] = useState(false)
  const [catForm, setCatForm] = useState({ nombre: '', descripcion: '', id_categoria_padre: '' })
  const [importResult, setImportResult] = useState(null)

  const totalStockMap = useMemo(() => {
    const m = {}
    stocks.forEach((s) => {
      m[s.id_producto] = (m[s.id_producto] || 0) + Number(s.cantidad_disponible || 0)
    })
    return m
  }, [stocks])

  const filteredProducts = useMemo(() => {
    const q = searchQ.trim().toLowerCase()
    return products.filter((p) => {
      if (filterCat !== 'ALL' && Number(p.id_categoria) !== Number(filterCat)) return false
      if (!q) return true
      return (
        p.nombre.toLowerCase().includes(q) ||
        p.codigo.toLowerCase().includes(q) ||
        (p.categoria_nombre || '').toLowerCase().includes(q)
      )
    })
  }, [products, searchQ, filterCat])

  const openCreateProduct = () => {
    setProdModal({
      mode: 'create',
      data: {
        codigo: '',
        nombre: '',
        descripcion: '',
        id_categoria: categories[0]?.id_categoria || 1,
        unidad_medida: 'UNIDAD',
        precio_venta: '',
      },
    })
  }

  const openEditProduct = (prod) => {
    setProdModal({
      mode: 'edit',
      data: {
        id_producto: prod.id_producto,
        codigo: prod.codigo,
        nombre: prod.nombre,
        descripcion: prod.descripcion || '',
        id_categoria: prod.id_categoria,
        unidad_medida: prod.unidad_medida,
        precio_venta: prod.precio_venta,
        activo: prod.activo,
      },
    })
  }

  const handleSaveProduct = async (e) => {
    e.preventDefault()
    const d = prodModal.data
    try {
      if (prodModal.mode === 'create') {
        await apiFetch('catalogo', '/products', {
          method: 'POST',
          body: JSON.stringify({
            ...d,
            id_categoria: Number(d.id_categoria),
            precio_venta: Number(d.precio_venta),
          }),
        })
        notify('Producto agregado al catálogo')
      } else {
        await apiFetch('catalogo', `/products/${d.id_producto}`, {
          method: 'PUT',
          body: JSON.stringify({
            ...d,
            id_categoria: Number(d.id_categoria),
            precio_venta: Number(d.precio_venta),
          }),
        })
        notify('Producto actualizado')
      }
      setProdModal(null)
      await onUpdated()
    } catch (err) {
      notify(err.message, true)
    }
  }

  const handleToggleProduct = async (prod) => {
    try {
      await apiFetch('catalogo', `/products/${prod.id_producto}`, {
        method: 'PUT',
        body: JSON.stringify({ activo: !prod.activo }),
      })
      await onUpdated()
      notify(prod.activo ? 'Producto dado de baja' : 'Producto reactivado')
    } catch (err) {
      notify(err.message, true)
    }
  }

  const handleCreateCategory = async (e) => {
    e.preventDefault()
    try {
      await apiFetch('catalogo', '/categories', {
        method: 'POST',
        body: JSON.stringify({
          nombre: catForm.nombre,
          descripcion: catForm.descripcion,
          id_categoria_padre: catForm.id_categoria_padre ? Number(catForm.id_categoria_padre) : null,
        }),
      })
      setCatForm({ nombre: '', descripcion: '', id_categoria_padre: '' })
      setCatModal(false)
      await onUpdated()
      notify('Categoría creada correctamente')
    } catch (err) {
      notify(err.message, true)
    }
  }

  const handleToggleCategory = async (cat) => {
    try {
      await apiFetch('catalogo', `/categories/${cat.id_categoria}`, {
        method: 'PUT',
        body: JSON.stringify({ activo: !cat.activo }),
      })
      await onUpdated()
      notify(cat.activo ? 'Categoría desactivada' : 'Categoría reactivada')
    } catch (err) {
      notify(err.message, true)
    }
  }

  const handleImportFile = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    const fd = new FormData()
    fd.append('file', file)
    fd.append('id_usuario', String(user?.id_usuario || 1))
    try {
      const res = await apiFetch('catalogo', '/products/import', { method: 'POST', body: fd })
      setImportResult(res)
      await onUpdated()
      notify(`Importación ${res.estado}: ${res.filas_validas} válidas, ${res.filas_error} errores`)
    } catch (err) {
      notify(err.message, true)
    }
  }

  const downloadTemplate = () => {
    downloadCsv(
      'plantilla_productos_andina.csv',
      ['codigo', 'nombre', 'descripcion', 'unidad_medida', 'precio_venta', 'id_categoria'],
      [
        ['FER-101', 'Segueta Bimetal 12"', 'Hoja de sierra 24 dientes', 'UNIDAD', '8500', '2'],
        ['FER-102', 'Silicona Transparente 280ml', 'Sellador multipropósito', 'UNIDAD', '16900', '5'],
      ]
    )
  }

  return (
    <div className="view-enter">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.75rem' }}>
        <div className="seg-tabs" role="tablist">
          <button type="button" className={`seg-tab ${subTab === 'productos' ? 'active' : ''}`} onClick={() => setSubTab('productos')}>
            Productos ({products.length})
          </button>
          <button type="button" className={`seg-tab ${subTab === 'categorias' ? 'active' : ''}`} onClick={() => setSubTab('categorias')}>
            Categorías ({categories.length})
          </button>
          {canManage && (
            <button type="button" className={`seg-tab ${subTab === 'importar' ? 'active' : ''}`} onClick={() => setSubTab('importar')}>
              Importar Excel / CSV
            </button>
          )}
        </div>

        {canManage && (
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button type="button" className="btn btn-secondary btn-sm" onClick={() => setCatModal(true)}>
              <Plus size={14} /> Categoría
            </button>
            <button type="button" className="btn btn-sm" onClick={openCreateProduct}>
              <Plus size={14} /> Nuevo Producto
            </button>
          </div>
        )}
      </div>

      {subTab === 'productos' && (
        <section className="panel">
          <div className="panel-header">
            <div>
              <h3 className="panel-title">Catálogo de Productos (RF01, RF12)</h3>
              <p className="panel-desc">Administra precios, unidades de medida, categorías y estado comercial</p>
            </div>
            <div style={{ display: 'flex', gap: '0.6rem', flexWrap: 'wrap' }}>
              <div className="search-bar" style={{ minWidth: '220px' }}>
                <Search size={15} />
                <input value={searchQ} onChange={(e) => setSearchQ(e.target.value)} placeholder="Buscar nombre o código..." />
              </div>
              <select style={{ width: 'auto' }} value={filterCat} onChange={(e) => setFilterCat(e.target.value)}>
                <option value="ALL">Todas las categorías</option>
                {categories.map((c) => (
                  <option key={c.id_categoria} value={c.id_categoria}>{c.nombre}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="table-wrapper" role="region" aria-label="Listado de productos" tabIndex={0}>
            <table>
              <thead>
                <tr>
                  <th>Código</th>
                  <th>Nombre</th>
                  <th>Categoría</th>
                  <th>Unidad</th>
                  <th>Stock Total</th>
                  <th>Precio Venta</th>
                  <th>Estado</th>
                  {canManage && <th>Acciones</th>}
                </tr>
              </thead>
              <tbody>
                {filteredProducts.map((p) => (
                  <tr key={p.id_producto}>
                    <td className="mono" style={{ fontWeight: 600 }}>{p.codigo}</td>
                    <td>
                      <div style={{ fontWeight: 600 }}>{p.nombre}</div>
                      {p.descripcion && <div style={{ fontSize: '0.75rem', color: 'var(--ink-muted)' }}>{p.descripcion}</div>}
                    </td>
                    <td>{p.categoria_nombre}</td>
                    <td className="mono">{p.unidad_medida}</td>
                    <td className="mono" style={{ fontWeight: 600 }}>{totalStockMap[p.id_producto] ?? 0}</td>
                    <td className="mono" style={{ fontWeight: 700 }}>{formatMoney(p.precio_venta)}</td>
                    <td>
                      <span className={`badge ${p.activo ? 'badge-sage' : 'badge-neutral'}`}>
                        {p.activo ? 'Activo' : 'Inactivo'}
                      </span>
                    </td>
                    {canManage && (
                      <td>
                        <div style={{ display: 'flex', gap: '0.4rem' }}>
                          <button type="button" className="btn btn-secondary btn-sm" onClick={() => openEditProduct(p)}>
                            <Edit3 size={13} /> Editar
                          </button>
                          <button type="button" className="btn btn-secondary btn-sm" onClick={() => handleToggleProduct(p)}>
                            {p.activo ? 'Baja' : 'Activar'}
                          </button>
                        </div>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {subTab === 'categorias' && (
        <section className="panel">
          <div className="panel-header">
            <div>
              <h3 className="panel-title">Categorías y Subcategorías (RF02)</h3>
              <p className="panel-desc">Clasificación jerárquica del catálogo de ferretería</p>
            </div>
          </div>
          <div className="table-wrapper" role="region" aria-label="Categorías" tabIndex={0}>
            <table>
              <thead>
                <tr><th>ID</th><th>Nombre</th><th>Categoría Padre</th><th>Descripción</th><th>Estado</th>{canManage && <th>Acción</th>}</tr>
              </thead>
              <tbody>
                {categories.map((c) => {
                  const padre = categories.find((x) => x.id_categoria === c.id_categoria_padre)
                  return (
                    <tr key={c.id_categoria}>
                      <td className="mono">#{c.id_categoria}</td>
                      <td style={{ fontWeight: 600 }}>{c.nombre}</td>
                      <td>{padre ? padre.nombre : 'Principal'}</td>
                      <td style={{ color: 'var(--ink-muted)' }}>{c.descripcion || '—'}</td>
                      <td><span className={`badge ${c.activo ? 'badge-sage' : 'badge-neutral'}`}>{c.activo ? 'Activa' : 'Inactiva'}</span></td>
                      {canManage && (
                        <td>
                          <button type="button" className="btn btn-secondary btn-sm" onClick={() => handleToggleCategory(c)}>
                            {c.activo ? 'Desactivar' : 'Activar'}
                          </button>
                        </td>
                      )}
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {subTab === 'importar' && (
        <section className="panel">
          <div className="panel-header">
            <div>
              <h3 className="panel-title">Importación Masiva desde Excel o CSV (RF17)</h3>
              <p className="panel-desc">Carga masiva con validación fila por fila y reporte de errores</p>
            </div>
            <button type="button" className="btn btn-secondary btn-sm" onClick={downloadTemplate}>
              <Download size={14} /> Descargar Plantilla CSV
            </button>
          </div>

          <label className="dropzone" style={{ cursor: 'pointer' }}>
            <Upload size={26} color="var(--accent)" />
            <div style={{ fontWeight: 600 }}>Selecciona un archivo .csv o .xlsx</div>
            <div style={{ fontSize: '0.8rem', color: 'var(--ink-muted)' }}>
              Columnas esperadas: <code>codigo, nombre, descripcion, unidad_medida, precio_venta, id_categoria</code>
            </div>
            <input type="file" accept=".csv,.xlsx" onChange={handleImportFile} style={{ display: 'none' }} />
          </label>

          {importResult && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              <div style={{ display: 'flex', gap: '0.6rem', flexWrap: 'wrap', alignItems: 'center' }}>
                <span className="badge badge-slate">Archivo: {importResult.nombre_archivo}</span>
                <span className="badge badge-sage">Válidas: {importResult.filas_validas}</span>
                <span className={`badge ${importResult.filas_error > 0 ? 'badge-crimson' : 'badge-neutral'}`}>
                  Errores: {importResult.filas_error}
                </span>
              </div>

              {importResult.detalles && (
                <div className="table-wrapper">
                  <table>
                    <thead><tr><th>Fila</th><th>Código</th><th>Estado</th><th>Detalle</th></tr></thead>
                    <tbody>
                      {importResult.detalles.map((d) => (
                        <tr key={d.id_detalle}>
                          <td className="mono">{d.numero_fila}</td>
                          <td className="mono">{d.codigo_fuente || '—'}</td>
                          <td><span className={`badge ${d.estado === 'VALIDA' ? 'badge-sage' : 'badge-crimson'}`}>{d.estado}</span></td>
                          <td>{d.mensaje_error || 'Importado correctamente'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </section>
      )}

      {/* Modal Producto (Crear / Editar) */}
      <Modal
        open={Boolean(prodModal)}
        onClose={() => setProdModal(null)}
        title={prodModal?.mode === 'edit' ? 'Editar Producto' : 'Nuevo Producto'}
      >
        {prodModal && (
          <form onSubmit={handleSaveProduct} style={{ display: 'flex', flexDirection: 'column', gap: '0.9rem' }}>
            <div className="form-grid">
              <div className="field">
                <label>Código SKU</label>
                <input
                  value={prodModal.data.codigo}
                  onChange={(e) => setProdModal({ ...prodModal, data: { ...prodModal.data, codigo: e.target.value } })}
                  placeholder="Ej. FER-011"
                  required
                />
              </div>
              <div className="field">
                <label>Unidad de Medida</label>
                <input
                  value={prodModal.data.unidad_medida}
                  onChange={(e) => setProdModal({ ...prodModal, data: { ...prodModal.data, unidad_medida: e.target.value } })}
                  required
                />
              </div>
            </div>
            <div className="field">
              <label>Nombre del Producto</label>
              <input
                value={prodModal.data.nombre}
                onChange={(e) => setProdModal({ ...prodModal, data: { ...prodModal.data, nombre: e.target.value } })}
                required
              />
            </div>
            <div className="form-grid">
              <div className="field">
                <label>Categoría</label>
                <select
                  value={prodModal.data.id_categoria}
                  onChange={(e) => setProdModal({ ...prodModal, data: { ...prodModal.data, id_categoria: e.target.value } })}
                >
                  {categories.map((c) => <option key={c.id_categoria} value={c.id_categoria}>{c.nombre}</option>)}
                </select>
              </div>
              <div className="field">
                <label>Precio de Venta (COP)</label>
                <input
                  type="number"
                  min="0"
                  value={prodModal.data.precio_venta}
                  onChange={(e) => setProdModal({ ...prodModal, data: { ...prodModal.data, precio_venta: e.target.value } })}
                  required
                />
              </div>
            </div>
            <div className="field">
              <label>Descripción</label>
              <input
                value={prodModal.data.descripcion}
                onChange={(e) => setProdModal({ ...prodModal, data: { ...prodModal.data, descripcion: e.target.value } })}
              />
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
              <button type="button" className="btn btn-secondary" onClick={() => setProdModal(null)}>Cancelar</button>
              <button type="submit" className="btn">Guardar Producto</button>
            </div>
          </form>
        )}
      </Modal>

      {/* Modal Categoría */}
      <Modal open={catModal} onClose={() => setCatModal(false)} title="Nueva Categoría / Subcategoría">
        <form onSubmit={handleCreateCategory} style={{ display: 'flex', flexDirection: 'column', gap: '0.9rem' }}>
          <div className="field">
            <label>Nombre</label>
            <input value={catForm.nombre} onChange={(e) => setCatForm({ ...catForm, nombre: e.target.value })} required />
          </div>
          <div className="field">
            <label>Categoría Padre (opcional)</label>
            <select value={catForm.id_categoria_padre} onChange={(e) => setCatForm({ ...catForm, id_categoria_padre: e.target.value })}>
              <option value="">Ninguna (Categoría principal)</option>
              {categories.filter((c) => !c.id_categoria_padre).map((c) => (
                <option key={c.id_categoria} value={c.id_categoria}>{c.nombre}</option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>Descripción</label>
            <input value={catForm.descripcion} onChange={(e) => setCatForm({ ...catForm, descripcion: e.target.value })} />
          </div>
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
            <button type="button" className="btn btn-secondary" onClick={() => setCatModal(false)}>Cancelar</button>
            <button type="submit" className="btn">Crear Categoría</button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
