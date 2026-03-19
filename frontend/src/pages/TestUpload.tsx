import { useState } from 'react';
import axios from 'axios';

const TestUpload = () => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState<any>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      setPreview(URL.createObjectURL(file));
      setError('');
      setResult(null);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      setError('Please select an image');
      return;
    }

    setLoading(true);
    setError('');

    const formData = new FormData();
    formData.append('image', selectedFile);

    try {
      console.log('Uploading...');
      
      const response = await axios.post(
        'http://localhost:3001/api/analysis/upload',
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        }
      );
      
      console.log('Success:', response.data);
      setResult(response.data.analysis);
    } catch (err: any) {
      console.error('Error:', err);
      setError(err.response?.data?.error || 'Upload failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 to-indigo-50 py-12 px-4">
      <div className="max-w-4xl mx-auto">
        <div className="bg-white rounded-2xl shadow-xl p-8">
          <h1 className="text-4xl font-bold mb-2 bg-gradient-to-r from-purple-600 to-indigo-600 bg-clip-text text-transparent">
            🧪 Test Environment - Skin Analysis
          </h1>
          <p className="text-gray-600 mb-8">No authentication required - Direct ML testing</p>

          {error && (
            <div className="bg-red-50 text-red-600 p-4 rounded-lg mb-6">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="border-2 border-dashed border-purple-300 rounded-xl p-8 text-center hover:border-purple-500 transition">
              <input
                type="file"
                accept="image/*"
                onChange={handleFileChange}
                className="hidden"
                id="file-upload"
              />
              <label htmlFor="file-upload" className="cursor-pointer">
                {preview ? (
                  <div>
                    <img src={preview} alt="Preview" className="max-h-64 mx-auto rounded-lg mb-4" />
                    <p className="text-purple-600 font-medium">Click to change image</p>
                  </div>
                ) : (
                  <div>
                    <svg className="w-16 h-16 mx-auto text-purple-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                    </svg>
                    <p className="text-lg font-medium text-gray-700 mb-2">
                      Click to upload face image
                    </p>
                    <p className="text-sm text-gray-500">PNG, JPG, JPEG</p>
                  </div>
                )}
              </label>
            </div>

            <button
              type="submit"
              disabled={!selectedFile || loading}
              className="w-full bg-gradient-to-r from-purple-600 to-indigo-600 text-white py-4 rounded-xl hover:from-purple-700 hover:to-indigo-700 transition disabled:opacity-50 text-lg font-semibold shadow-lg"
            >
              {loading ? (
                <span className="flex items-center justify-center">
                  <svg className="animate-spin h-5 w-5 mr-3" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Analyzing...
                </span>
              ) : (
                '🔍 Analyze Skin Type'
              )}
            </button>
          </form>

          {result && (
            <div className="mt-8 bg-gradient-to-r from-purple-50 to-indigo-50 rounded-xl p-6 border-2 border-purple-200">
              <h2 className="text-2xl font-bold mb-4 text-purple-900">✨ Analysis Results</h2>
              
              <div className="grid md:grid-cols-2 gap-6 mb-6">
                <div className="bg-white rounded-lg p-4 shadow">
                  <p className="text-gray-600 text-sm mb-1">Skin Type</p>
                  <p className="text-3xl font-bold text-purple-600">{result.skin_type}</p>
                </div>
                <div className="bg-white rounded-lg p-4 shadow">
                  <p className="text-gray-600 text-sm mb-1">Confidence</p>
                  <p className="text-3xl font-bold text-indigo-600">{result.confidence}%</p>
                </div>
              </div>

              <div className="bg-white rounded-lg p-4 shadow">
                <p className="text-gray-900 font-semibold mb-3">💡 Recommendations:</p>
                <ul className="space-y-2">
                  {JSON.parse(result.recommendations).map((rec: string, i: number) => (
                    <li key={i} className="flex items-start">
                      <span className="text-purple-600 font-bold mr-2">{i + 1}.</span>
                      <span className="text-gray-700">{rec}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="mt-4 text-center">
                <button
                  onClick={() => {
                    setResult(null);
                    setSelectedFile(null);
                    setPreview(null);
                  }}
                  className="bg-white text-purple-600 px-6 py-2 rounded-lg hover:bg-purple-50 transition font-medium border-2 border-purple-200"
                >
                  🔄 Analyze Another Image
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default TestUpload;