"use client";
import React, { useEffect, useState, useCallback } from 'react';
import axios from 'axios';

interface SettingsForm {
  max_workers: number;
  max_retries: number;
  backoff_factor: number;
  output_dir: string;
}

interface ServerError { field?: string; message: string; }

const DEFAULTS: SettingsForm = { max_workers: 5, max_retries: 3, backoff_factor: 2.0, output_dir: './subtitles' };

const numberBounds = {
  max_workers: { min: 1, max: 20 },
  max_retries: { min: 1, max: 10 },
  backoff_factor: { min: 1.0, max: 10.0 }
};

const SettingsPage: React.FC = () => {
  const [form, setForm] = useState<SettingsForm | null>(null);
  const [initial, setInitial] = useState<SettingsForm | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [errors, setErrors] = useState<Record<string,string>>({});
  const [serverError, setServerError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const backendBase = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8004').replace(/\/$/, '');

  const fetchSettings = useCallback(async () => {
    setLoading(true);
    setServerError(null);
    try {
      const res = await axios.get(`${backendBase}/jobs/settings`);
      setForm(res.data);
      setInitial(res.data);
    } catch (e:any) {
      // Fallback to defaults but still allow editing & saving
      setForm(DEFAULTS);
      setInitial(DEFAULTS); // ensure buttons work
      setServerError(e?.response?.data?.detail || 'Failed to load settings (using defaults)');
    } finally {
      setLoading(false);
    }
  }, [backendBase]);

  useEffect(()=>{ fetchSettings(); }, [fetchSettings]);

  const updateField = <K extends keyof SettingsForm>(key: K, value: SettingsForm[K]) => {
    if (!form) return;
    const updated = { ...form, [key]: value };
    setForm(updated);
    validate(updated);
    setSuccess(false);
  };

  const validate = (f: SettingsForm) => {
    const newErrors: Record<string,string> = {};
    if (f.max_workers < numberBounds.max_workers.min || f.max_workers > numberBounds.max_workers.max) newErrors.max_workers = `Must be ${numberBounds.max_workers.min}-${numberBounds.max_workers.max}`;
    if (f.max_retries < numberBounds.max_retries.min || f.max_retries > numberBounds.max_retries.max) newErrors.max_retries = `Must be ${numberBounds.max_retries.min}-${numberBounds.max_retries.max}`;
    if (f.backoff_factor < numberBounds.backoff_factor.min || f.backoff_factor > numberBounds.backoff_factor.max) newErrors.backoff_factor = `Must be ${numberBounds.backoff_factor.min}-${numberBounds.backoff_factor.max}`;
    if (!f.output_dir.trim()) newErrors.output_dir = 'Required';
    setErrors(newErrors);
    return newErrors;
  };

  const hasChanges = !!(form && initial && JSON.stringify(form) !== JSON.stringify(initial));

  const save = async () => {
    if (!form) return;
    const errs = validate(form);
    if (Object.keys(errs).length) return;
    setSaving(true);
    setServerError(null);
    try {
      const res = await axios.post(`${backendBase}/jobs/settings`, form);
      setForm(res.data);
      setInitial(res.data);
      setSuccess(true);
    } catch (e:any) {
      setServerError(e?.response?.data?.detail || 'Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  if (loading || !form) {
    return <div style={{display:'flex',flexDirection:'column',alignItems:'center',justifyContent:'center',minHeight:'300px'}}><div className="spinner"/>Loading settings...</div>;
  }

  return (
    <div style={{maxWidth:'800px', margin:'0 auto', padding:'32px', fontFamily:'-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif'}}>
      <h1 style={{margin:'0 0 8px', fontSize:'2rem', color:'#111827'}}>Settings</h1>
      <p style={{margin:'0 0 24px', color:'#6b7280', fontSize:'14px'}}>Configure worker processing parameters and retry behavior.</p>

      {serverError && (
        <div style={{background:'#fef2f2', border:'1px solid #fee2e2', padding:'12px 16px', borderRadius:'8px', color:'#991b1b', marginBottom:'16px'}}>{serverError}</div>
      )}
      {success && (
        <div style={{background:'#ecfdf5', border:'1px solid #a7f3d0', padding:'12px 16px', borderRadius:'8px', color:'#065f46', marginBottom:'16px'}}>Settings saved.</div>
      )}

      <div style={{display:'grid', gap:'20px'}}>
        <Field label="Max Workers" description="Number of parallel workers processing videos." error={errors.max_workers}>
          <input type="number" value={form.max_workers} min={1} max={20} onChange={e=>updateField('max_workers', Number(e.target.value))} />
        </Field>
        <Field label="Max Retries" description="Maximum attempts per failed video before marking failed." error={errors.max_retries}>
          <input type="number" value={form.max_retries} min={1} max={10} onChange={e=>updateField('max_retries', Number(e.target.value))} />
        </Field>
        <Field label="Backoff Factor" description="Multiplier for exponential backoff between retries." error={errors.backoff_factor}>
          <input type="number" step="0.1" value={form.backoff_factor} min={1} max={10} onChange={e=>updateField('backoff_factor', Number(e.target.value))} />
        </Field>
        <Field label="Output Directory" description="Directory where subtitle files are written." error={errors.output_dir}>
          <input value={form.output_dir} onChange={e=>updateField('output_dir', e.target.value)} />
        </Field>
      </div>

      <div style={{display:'flex', gap:'12px', marginTop:'32px'}}>
        <button onClick={save} disabled={!hasChanges || saving || Object.keys(errors).length>0} style={{background:'#2563eb', color:'#fff', padding:'10px 18px', border:'none', borderRadius:'8px', fontWeight:600, cursor: (!hasChanges || saving || Object.keys(errors).length>0)?'not-allowed':'pointer'}}>
          {saving ? 'Saving...' : 'Save Settings'}
        </button>
        <button onClick={()=>{ if(initial) setForm(initial); setErrors({}); setSuccess(false); }} disabled={!hasChanges || saving} style={{background:'#f3f4f6', color:'#374151', padding:'10px 18px', border:'none', borderRadius:'8px', fontWeight:500, cursor: (!hasChanges || saving)?'not-allowed':'pointer'}}>
          Reset
        </button>
      </div>

      <div style={{marginTop:'48px', fontSize:'12px', color:'#6b7280'}}>
        <p>Note: Worker pool size changes will affect new processing loops. Existing running tasks continue until completion.</p>
      </div>

      <style jsx>{`
        input { width:100%; padding:10px 12px; border:1px solid #d1d5db; border-radius:8px; font-size:14px; }
        input:focus { outline:none; border-color:#2563eb; box-shadow:0 0 0 1px #2563eb; }
        .spinner { width:40px;height:40px;border:4px solid #f3f4f6;border-top:4px solid #2563eb;border-radius:50%;animation:spin 1s linear infinite;margin-bottom:12px; }
        @keyframes spin {0%{transform:rotate(0deg);}100%{transform:rotate(360deg);}}
      `}</style>
    </div>
  );
};

const Field: React.FC<{label:string; description?:string; error?:string; children: React.ReactNode}> = ({label, description, error, children}) => (
  <label style={{display:'block'}}>
    <div style={{display:'flex', justifyContent:'space-between', alignItems:'flex-end'}}>
      <span style={{fontSize:'14px', fontWeight:600, color:'#374151'}}>{label}</span>
      {error && <span style={{fontSize:'11px', color:'#b91c1c'}}>{error}</span>}
    </div>
    {description && <div style={{fontSize:'12px', color:'#6b7280', margin:'4px 0 6px'}}>{description}</div>}
    {children}
  </label>
);

export default SettingsPage;
