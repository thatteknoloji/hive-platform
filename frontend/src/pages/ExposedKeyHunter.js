import React, { useState } from 'react';
import API from '../api';

const ExposedKeyHunter = () => {
  const [query, setQuery] = useState('openai');
  const [limit, setLimit] = useState(50);
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedKey, setSelectedKey] = useState(null);

  const startScan = async () => {
    setLoading(true);
    try {
      const apiKey = localStorage.getItem('apiKey');
      const response = await API.post(`/api/hunter/scan`, { query, limit: parseInt(limit) }, {
        headers: { 'X-API-Key': apiKey }
      });
      setResults(response.data.results || []);
    } catch (error) {
      console.error('Scan failed:', error);
      alert('Tarama başarısız: ' + error.message);
    }
    setLoading(false);
  };

  const showTemplate = (key) => {
    setSelectedKey(key);
  };

  const copyTemplate = () => {
    if (selectedKey) {
      const template = `Konu: Güvenlik Açığı Tespiti - ${selectedKey.type}

Merhaba,

${selectedKey.repo_url} reposunda bir API anahtarınız açıkta.

- Tip: ${selectedKey.type}
- Anahtar: ${selectedKey.key_masked}
- Dosya: ${selectedKey.file_path}
- Satır: ${selectedKey.line}

Herhangi bir işlem yapmadık, sadece bilgi amaçlı.

İyi çalışmalar.`;
      navigator.clipboard.writeText(template);
      alert('Mail şablonu kopyalandı! Kendi mailinize yapıştırıp gönderebilirsiniz.');
    }
  };

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-4">Exposed Key Hunter</h1>
      <p className="text-gray-600 mb-4">GitHub'da açıkta kalmış API key'lerini Kingfisher ile tespit eder. ASLA otomatik iptal veya mail göndermez.</p>

      <div className="flex gap-4 mb-6">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Aranacak kelime (openai, aws, github, stripe...)"
          className="border p-2 rounded flex-1"
        />
        <input
          type="number"
          value={limit}
          onChange={(e) => setLimit(e.target.value)}
          placeholder="Limit"
          className="border p-2 rounded w-24"
        />
        <button
          onClick={startScan}
          disabled={loading}
          className="bg-blue-500 text-white px-4 py-2 rounded disabled:bg-gray-400"
        >
          {loading ? 'Taranıyor...' : 'Tarama Başlat'}
        </button>
      </div>

      {results.length > 0 && (
        <div className="mb-4 p-3 bg-green-100 text-green-700 rounded">
          ✅ {results.length} adet VALID (çalışan) API key bulundu. Hiçbir işlem yapılmadı.
        </div>
      )}

      {results.length === 0 && !loading && (
        <div className="p-3 bg-yellow-50 text-yellow-700 rounded">
          Henüz sonuç yok. Yukarıdan bir sorgu girip "Tarama Başlat"a tıklayın.
        </div>
      )}

      <div className="space-y-3">
        {results.map((key, idx) => {
          if (key.type === 'error') {
            return (
              <div key={idx} className="border rounded p-4 bg-red-50 border-red-200">
                <p className="text-red-700"><strong>Hata:</strong> {key.message}</p>
              </div>
            );
          }
          return (
            <div key={idx} className="border rounded p-4 bg-white shadow-sm">
              <div className="flex justify-between items-start">
                <div>
                  <span className="font-mono bg-gray-100 px-2 py-1 rounded text-sm">{key.type}</span>
                  <span className="ml-2 text-green-600 text-sm">✓ VALID</span>
                  <div className="mt-2">
                    <p className="text-sm"><strong>Repo:</strong> {key.repo_url}</p>
                    <p className="text-sm"><strong>Dosya:</strong> {key.file_path}</p>
                    <p className="text-sm"><strong>Satır:</strong> {key.line}</p>
                    <p className="text-sm"><strong>Anahtar:</strong> {key.key_masked}</p>
                  </div>
                </div>
                <button
                  onClick={() => showTemplate(key)}
                  className="bg-gray-500 text-white px-3 py-1 rounded text-sm"
                >
                  Mail Şablonunu Göster
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {selectedKey && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-2xl w-full mx-4">
            <h2 className="text-xl font-bold mb-4">Mail Şablonu</h2>
            <p className="text-sm text-gray-600 mb-2">Bu şablonu kopyalayıp kendi mailinizden gönderebilirsiniz.</p>
            <textarea
              readOnly
              value={`Konu: Güvenlik Açığı Tespiti - ${selectedKey.type}

Merhaba,

${selectedKey.repo_url} reposunda bir API anahtarınız açıkta.

- Tip: ${selectedKey.type}
- Anahtar: ${selectedKey.key_masked}
- Dosya: ${selectedKey.file_path}
- Satır: ${selectedKey.line}

Herhangi bir işlem yapmadık, sadece bilgi amaçlı.

İyi çalışmalar.`}
              className="w-full h-64 border rounded p-3 font-mono text-sm mb-4"
            />
            <div className="flex gap-2 justify-end">
              <button
                onClick={copyTemplate}
                className="bg-blue-500 text-white px-4 py-2 rounded"
              >
                Kopyala
              </button>
              <button
                onClick={() => setSelectedKey(null)}
                className="bg-gray-300 px-4 py-2 rounded"
              >
                Kapat
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ExposedKeyHunter;
