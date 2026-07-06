import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Image as ImageIcon } from 'lucide-react';

const Gallery = () => {
  const [webtoons, setWebtoons] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchWebtoons = async () => {
      try {
        const response = await axios.get('/api/webtoons');
        setWebtoons(response.data.webtoons);
      } catch (err) {
        setError('갤러리를 불러오는데 실패했습니다.');
      } finally {
        setLoading(false);
      }
    };

    fetchWebtoons();
  }, []);

  const formatDate = (dateStr) => {
    if (!dateStr || dateStr.length < 15) return dateStr;
    // 20260705_005141 -> 2026-07-05 00:51
    return `${dateStr.substring(0,4)}-${dateStr.substring(4,6)}-${dateStr.substring(6,8)} ${dateStr.substring(9,11)}:${dateStr.substring(11,13)}`;
  };

  return (
    <div className="main-content" style={{ maxWidth: '1200px' }}>
      <div className="header-section" style={{ marginBottom: '2rem' }}>
        <h1 style={{ fontSize: '2.5rem' }}>작품 갤러리</h1>
        <p>AI가 생성한 결과물들을 한눈에 모아보세요.</p>
      </div>

      <div className="glass-panel">
        <div className="panel-header" style={{ marginBottom: '2rem' }}>
          <ImageIcon className="icon" size={24} />
          <h2>생성된 릴스 목록</h2>
        </div>

        {loading ? (
          <div style={{ textAlign: 'center', padding: '3rem', color: '#94a3b8' }}>
            <div className="loader" style={{ margin: '0 auto 1rem' }}></div>
            로딩 중...
          </div>
        ) : error ? (
          <div className="alert alert-error">{error}</div>
        ) : webtoons.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '3rem', color: '#94a3b8' }}>
            아직 생성된 결과물이 없습니다.
          </div>
        ) : (
          <div className="gallery-grid">
            {webtoons.map((toon) => (
              <a href={toon.thumbnail_url} target="_blank" rel="noreferrer" key={toon.id} className="webtoon-card">
                <img src={toon.thumbnail_url} alt="Thumbnail" className="webtoon-image" />
                <div className="webtoon-overlay">
                  <div className="webtoon-title">카드뉴스 릴스</div>
                  <div className="webtoon-date">{formatDate(toon.created_at)}</div>
                </div>
              </a>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default Gallery;
