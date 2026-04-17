import { useState } from "react";
import axios from "axios";
import { motion } from "framer-motion";
import ReactMarkdown from "react-markdown";
import { SearchCheck, FlaskConical, Stethoscope, AlertTriangle } from "lucide-react";
import "./App.css";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:5000";

const formatRawText = (text) => {
  if (!text) return "";
  let formatted = text;
  formatted = formatted.replace(/(Inclusion Criteria:|Exclusion Criteria:)/gi, '\n\n### $1\n');
  formatted = formatted.replace(/\n\s*(\d+\.)\s/g, '\n$1 ');
  return formatted.trim();
};

function App() {
  const [form, setForm] = useState({
    patientName: "", disease: "", intent: "", additionalQuery: "", location: "", message: "",
    mode: "clinical"
  });
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  
  const [activeTab, setActiveTab] = useState("analysis");
  const [modalContent, setModalContent] = useState(null);

  const handleChange = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true); setError(""); setResult(null); setActiveTab("analysis");
    try {
      const { data } = await axios.post(`${API_URL}/api/chat/message`, form, { timeout: 600000 });
      if (data.success) setResult(data.data);
      else throw new Error(data.message || "Analysis failed");
    } catch (err) {
      setError(err?.response?.data?.message || "Timeout or Connection Error.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page">
      <div className="ambient ambient-a" />
      <div className="ambient ambient-b" />

      <motion.header className="hero" initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }}>
        <h1 style={{ fontSize: '4.5rem', margin: 0, letterSpacing: '-2px', fontWeight: '900', textTransform: 'uppercase' }}>
          <span style={{ color: '#000000' }}>CURA</span>
          <span style={{ color: '#e11d48' }}>LINK</span>
        </h1>
        <p style={{ color: '#475569', fontWeight: '600', marginTop: '5px', fontSize: '1.1rem' }}>
          AI Medical Research Assistant · MERN + Open Source LLM
        </p>
      </motion.header>

      <section className="grid">
        <motion.form className="panel form-panel" onSubmit={handleSubmit}>
          <h2>Patient Research Context</h2>
          <div className="field-grid">
            <label>
              <span>Patient Name</span>
              <input name="patientName" value={form.patientName} onChange={handleChange} placeholder="e.g. John Doe" required />
            </label>
            <label>
              <span>Disease</span>
              <input name="disease" value={form.disease} onChange={handleChange} placeholder="e.g. Parkinsons disease" required />
            </label>
            <label>
              <span>Intent</span>
              <input name="intent" value={form.intent} onChange={handleChange} placeholder="e.g. latest deep brain stimulation treatments" required />
            </label>
            <label>
              <span>Location</span>
              <input name="location" value={form.location} onChange={handleChange} placeholder="e.g. Ahmedabad, India" />
            </label>
            <label>
              <span>Additional Query</span>
              <input name="additionalQuery" value={form.additionalQuery} onChange={handleChange} placeholder="e.g. Focus on non-invasive options" />
            </label>
            
            <label>
              <span>Explanation Mode</span>
              <select name="mode" value={form.mode} onChange={handleChange}>
                <option value="clinical">🏥 Clinical (Professional)</option>
                <option value="elif">🏠 ELIF (Patient Friendly)</option>
              </select>
            </label>
          </div>
          <label className="message-field">
            <span>Follow-up Question</span>
            <textarea name="message" value={form.message} onChange={handleChange} placeholder="e.g. How can the patient manage daily tremors?" rows="3" required />
          </label>
          <button disabled={loading} type="submit" className="no-print">
            {loading ? "Analyzing Deep Research..." : "Run Deep Medical Research"}
          </button>
          {error && <p className="error"><AlertTriangle size={16} /> {error}</p>}
        </motion.form>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '15px', minWidth: '0' }}>
          
          {result && (
            <div className="no-print" style={{ display: 'flex', gap: '10px', background: '#ffffff', padding: '12px', borderRadius: '12px', overflowX: 'auto', alignItems: 'center', border: '1px solid #e2e8f0', boxShadow: '0 4px 6px rgba(0,0,0,0.05)' }}>
              <button onClick={() => setActiveTab("analysis")} style={{ background: activeTab === "analysis" ? '#000000' : 'transparent', border: '2px solid #000000', padding: '8px 16px', borderRadius: '8px', cursor: 'pointer', color: activeTab === "analysis" ? 'white' : '#000000', fontWeight: 'bold' }}>🧠 Analysis</button>
              <button onClick={() => setActiveTab("publications")} style={{ background: activeTab === "publications" ? '#000000' : 'transparent', border: '2px solid #000000', padding: '8px 16px', borderRadius: '8px', cursor: 'pointer', color: activeTab === "publications" ? 'white' : '#000000', fontWeight: 'bold' }}>📚 Publications</button>
              <button onClick={() => setActiveTab("trials")} style={{ background: activeTab === "trials" ? '#000000' : 'transparent', border: '2px solid #000000', padding: '8px 16px', borderRadius: '8px', cursor: 'pointer', color: activeTab === "trials" ? 'white' : '#000000', fontWeight: 'bold' }}>🏥 Clinical Trials</button>
              
              {activeTab === "analysis" && (
                <button onClick={() => setModalContent({ type: 'analysis', data: result.analysis })} style={{ marginLeft: 'auto', background: '#e11d48', border: 'none', padding: '10px 16px', borderRadius: '8px', cursor: 'pointer', color: 'white', fontWeight: 'bold' }}>🔍 Expand Report</button>
              )}

              <button onClick={() => window.print()} style={{ marginLeft: activeTab === "analysis" ? '10px' : 'auto', background: '#28a745', border: 'none', padding: '10px 16px', borderRadius: '8px', cursor: 'pointer', color: 'white', fontWeight: 'bold' }}>📄 Export PDF</button>
            </div>
          )}

          {/* 🔥 1. ANALYSIS SECTION */}
          <div className="panel print-section" style={{ display: (!result || activeTab === "analysis") ? 'block' : 'none', maxHeight: '600px', overflowY: 'auto' }}>
            {!result ? (
              <div className="placeholder">
                <div>
                  <Stethoscope size={48} color="#cbd5e1" style={{ marginBottom: '15px' }} />
                  <h3 style={{ color: '#000000', margin: 0 }}>Awaiting Input</h3>
                  <p style={{ color: '#64748b', marginTop: '5px' }}>Submit a query to begin AI research.</p>
                </div>
              </div>
            ) : (
              <>
                <div className="stats no-print">
                  <div><SearchCheck size={16} /> Candidates: {result.meta?.total_candidates_fetched || 0}</div>
                  <div><FlaskConical size={16} /> Time: {result.meta?.executionTime || result.meta?.pipeline_latencyMs + 'ms'}</div>
                </div>
                <article className="markdown" style={{ whiteSpace: "pre-wrap" }}>
                  <ReactMarkdown>{result.analysis}</ReactMarkdown>
                </article>
              </>
            )}
          </div>

          {/* 🔥 2. PUBLICATIONS SECTION */}
          {result && (
            <div className="panel print-section" style={{ display: activeTab === "publications" ? 'block' : 'none', maxHeight: '600px', overflowY: 'auto' }}>
              <h3 style={{ position: 'sticky', top: '-28px', backgroundColor: '#ffffff', padding: '20px 0 10px 0', zIndex: 10, margin: '-28px 0 15px 0' }}>Top Publications</h3>
              {result.sources?.filter(s => s.source !== "ClinicalTrials.gov").map((item, i) => (
                <div className="result-card" key={i}>
                  {/* Title is now a clickable link! */}
                  <a href={item.url} target="_blank" rel="noreferrer" className="pdf-link" style={{ textDecoration: 'none' }}>
                    <strong style={{ fontSize: '1.1em', display: 'block', marginBottom: '8px', color: '#0f172a' }}>{item.title}</strong>
                  </a>
                  <span style={{ fontSize: '0.85em', color: '#64748b', fontWeight: '600' }}>{item.source} · {item.year || "N/A"} · Score: {item.score?.toFixed(1) || 0}</span>
                  
                  <div className="no-print" style={{ display: 'flex', gap: '15px', marginTop: '20px', alignItems: 'center' }}>
                    <a href={item.url} target="_blank" rel="noreferrer" style={{ color: '#000000', fontSize: '0.95em', textDecoration: 'underline', fontWeight: '700' }}>Open Source</a>
                    <button onClick={() => setModalContent({ type: 'source', data: item })} style={{ background: '#e11d48', border: 'none', padding: '8px 16px', borderRadius: '6px', cursor: 'pointer', color: 'white', fontSize: '0.9em', fontWeight: 'bold' }}>🔍 Expand Detail</button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* 🔥 3. CLINICAL TRIALS SECTION */}
          {result && (
            <div className="panel print-section" style={{ display: activeTab === "trials" ? 'block' : 'none', maxHeight: '600px', overflowY: 'auto' }}>
              <h3 style={{ position: 'sticky', top: '-28px', backgroundColor: '#ffffff', padding: '20px 0 10px 0', zIndex: 10, margin: '-28px 0 15px 0' }}>Top Clinical Trials</h3>
              {result.sources?.filter(s => s.source === "ClinicalTrials.gov").map((item, i) => (
                <div className="result-card" key={i}>
                  {/* Title is now a clickable link! */}
                  <a href={item.url} target="_blank" rel="noreferrer" className="pdf-link" style={{ textDecoration: 'none' }}>
                    <strong style={{ fontSize: '1.1em', display: 'block', marginBottom: '8px', color: '#0f172a' }}>{item.title}</strong>
                  </a>
                  <span style={{ fontSize: '0.85em', color: '#64748b', fontWeight: '600' }}>{item.location || "Global"} · Score: {item.score?.toFixed(1) || 0}</span>
                  
                  {item.location?.toLowerCase().includes(form.location?.toLowerCase()) && 
                    <p style={{ color: '#e11d48', fontSize: '0.9em', margin: '8px 0', fontWeight: '800' }}>📍 Nearby Opportunity</p>}
                  
                  <div className="no-print" style={{ display: 'flex', flexWrap: 'wrap', gap: '15px', marginTop: '20px', alignItems: 'center' }}>
                    <a href={item.url} target="_blank" rel="noreferrer" style={{ color: '#000000', fontSize: '0.95em', textDecoration: 'underline', fontWeight: '700' }}>View Trial Page</a>
                    <button onClick={() => setModalContent({ type: 'source', data: item })} style={{ background: '#e11d48', border: 'none', padding: '8px 16px', borderRadius: '6px', cursor: 'pointer', color: 'white', fontSize: '0.9em', fontWeight: 'bold' }}>🔍 Expand Detail</button>
                    <a href={`http://googleusercontent.com/maps.google.com/?q=${encodeURIComponent(item.location)}`} target="_blank" rel="noreferrer" style={{ background: '#000000', border: 'none', padding: '8px 16px', borderRadius: '6px', cursor: 'pointer', color: 'white', fontSize: '0.9em', fontWeight: 'bold', textDecoration: 'none' }}>🗺️ Locate on Map</a>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </section>

      {/* MODAL OVERLAY */}
      {modalContent && (
        <div style={{ position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh', backgroundColor: 'rgba(0, 0, 0, 0.85)', zIndex: 9999, display: 'flex', justifyContent: 'center', alignItems: 'center', padding: '20px', backdropFilter: 'blur(5px)' }}>
          <div style={{ backgroundColor: '#ffffff', width: '100%', maxWidth: '900px', maxHeight: '90vh', borderRadius: '16px', padding: '35px', overflowY: 'auto', position: 'relative', boxShadow: '0 25px 50px -12px rgba(0,0,0,0.5)' }}>
            <button onClick={() => setModalContent(null)} style={{ position: 'absolute', top: '20px', right: '20px', background: '#000000', color: 'white', border: 'none', borderRadius: '50%', width: '40px', height: '40px', cursor: 'pointer', fontWeight: 'bold', fontSize: '1.2em' }}>✕</button>
            {modalContent.type === 'analysis' && (
              <article className="markdown" style={{ fontSize: '1.15em', lineHeight: '1.8', color: '#334155', whiteSpace: 'pre-wrap' }}><ReactMarkdown>{modalContent.data}</ReactMarkdown></article>
            )}
            {modalContent.type === 'source' && (
              <>
                <h2 style={{ borderBottom: '3px solid #e11d48', paddingBottom: '15px', marginBottom: '15px' }}>{modalContent.data.title}</h2>
                <p><strong>Source:</strong> {modalContent.data.source} · <strong>Year:</strong> {modalContent.data.year}</p>
                {modalContent.data.abstract_text && <ReactMarkdown>{formatRawText(modalContent.data.abstract_text)}</ReactMarkdown>}
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default App;