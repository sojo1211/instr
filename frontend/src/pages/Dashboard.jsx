import React, { useState, useEffect } from 'react';
import { FileText, Wand2 } from 'lucide-react';
import axios from 'axios';

const DEFAULT_PROMPT = `카드 1.
배경 이미지: 서울 도심, 흐린 하늘, 출근길, 경제 뉴스 분위기의 사진

텍스트:
2026년 7월 6일 (@내가 명령하는 날짜로 변경해서 제작)
주요 시사 / 뉴스

☀️ 오늘의 날씨
서울: 최저 24° / 최고 29°

💹 오늘의 증시
KOSPI 8,088.34 ▲ +5.76%
KOSDAQ 868.41 ▲ +0.19%
NASDAQ 25,832.67 ▼ -0.80%
원/달러 환율 1,530.00 ▼ -0.81%

카드 2.
배경 이미지: 내가 주는 기사에 어울리는 이미지

텍스트:
📰 오늘의 뉴스 

🎈 “삼전하닉 하루 13% 급등락, 차라리 6% 적금 들걸” 하락장 처음 맛본 ‘포모 개미’의 후회
https://n.news.naver.com/article/014/0005543665?cds=news_edit
(@이렇게 헤드라인이랑 링크를 주면 크롤링해서 기사 내용 요약 후 카드뉴스로 제작)

카드 3.
배경 이미지: 내가 주는 기사에 어울리는 이미지

텍스트:
📰 오늘의 뉴스

🎈 혼자 사는 30대 남성, 고혈압에 가장 취약
https://www.chosun.com/national/welfare-medical/2026/07/05/QOAKL35OL5AFRNJAFFKQOMLVMM/
(@이렇게 헤드라인이랑 링크를 주면 크롤링해서 기사 내용 요약 후 카드뉴스로 제작)

카드 4.
배경 이미지: 차분한 하늘, 책상 위 다이어리, 잔잔한 자연광, 고급스러운 명언 카드 분위기

텍스트:
🤍 오늘의 명언

겸손함은
아름다움의 요새이다.

- 데마데스 -

오늘도 단단하고 겸손하게,
나의 하루를 가치 있게 만들어가세요.`;

const Dashboard = () => {
  const [textPrompt, setTextPrompt] = useState(DEFAULT_PROMPT);
  const [loading, setLoading] = useState(false);
  const [loadingText, setLoadingText] = useState('생성 중...');
  const [loadingPanels, setLoadingPanels] = useState([]);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [resultImg, setResultImg] = useState('');
  const [videoUrl, setVideoUrl] = useState('');
  const [resultPanels, setResultPanels] = useState([]);

  const handleSubmit = async () => {
    if (!textPrompt.trim()) {
      setError('텍스트 프롬프트를 입력해주세요.');
      return;
    }

    setLoading(true);
    setLoadingText('서버로 작업 전송 중...');
    setLoadingPanels([]);
    setError('');
    setSuccess('');
    setResultImg('');
    setVideoUrl('');
    setResultPanels([]);

    const formData = new FormData();
    formData.append('text_prompt', textPrompt);

    try {
      const response = await axios.post('/api/generate', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      if (response.data.success && response.data.task_id) {
        const taskId = response.data.task_id;
        
        // Polling
        const checkProgress = async () => {
          try {
            const res = await axios.get(`/api/progress/${taskId}`);
            const { status, message, final_image_url, panels, video_url } = res.data;
            
            if (message) setLoadingText(message);
            if (panels) setLoadingPanels(panels);
            
            if (status === 'completed') {
              clearInterval(interval);
              setSuccess('카드뉴스 릴스 생성이 완료되었습니다!');
              setResultImg(final_image_url);
              if (video_url) setVideoUrl(video_url);
              if (panels) setResultPanels(panels);
              setLoading(false);
            } else if (status === 'error') {
              clearInterval(interval);
              setError(message || '생성 중 오류가 발생했습니다.');
              setLoading(false);
            }
          } catch (e) {
            console.error('Progress check failed:', e);
          }
        };

        checkProgress();
        const interval = setInterval(checkProgress, 2000);
      }
    } catch (err) {
      setError(err.response?.data?.detail || '서버 오류가 발생했습니다.');
      setLoading(false);
    }
  };

  return (
    <div className="main-content">
      {loading && (
        <div className="loading-overlay">
          <div className="loader"></div>
          <div className="loading-text">{loadingText}</div>
          {loadingPanels.length > 0 && (
            <div className="loading-panels-grid">
              {loadingPanels.map((url, idx) => (
                <img key={idx} src={url} alt={`진행중인 컷 ${idx + 1}`} />
              ))}
            </div>
          )}
        </div>
      )}

      <div className="header-section">
        <h1>카드뉴스 릴스 메이커</h1>
        <p>복사+붙여넣기 한 번으로 평일 매일 고품질 카드뉴스와 인스타 릴스를 완성하세요!</p>
      </div>

      <div className="glass-panel">
        <div className="panel-header" style={{ marginBottom: '1rem' }}>
          <FileText className="icon" size={24} />
          <h2>오늘의 내용 입력 (텍스트 프롬프트)</h2>
        </div>
        <p style={{ color: '#94a3b8', marginBottom: '1rem', fontSize: '0.9rem' }}>
          아래 양식에 맞춰 [CARD 1], [CARD 2] 등의 태그와 함께 내용을 입력해주시면, AI가 문맥에 맞는 배경 이미지를 자동으로 찾아 글자를 렌더링합니다.
        </p>

        <textarea
          value={textPrompt}
          onChange={(e) => setTextPrompt(e.target.value)}
          placeholder="[CARD 1] 등 양식에 맞춰 내용을 입력하세요..."
          style={{
            width: '100%',
            height: '400px',
            backgroundColor: 'rgba(255, 255, 255, 0.05)',
            color: 'white',
            border: '1px solid rgba(255, 255, 255, 0.1)',
            borderRadius: '12px',
            padding: '1rem',
            fontFamily: 'inherit',
            fontSize: '0.95rem',
            lineHeight: '1.5',
            resize: 'vertical',
            marginBottom: '1rem'
          }}
        />

        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', alignItems: 'center' }}>
          {error && <div className="alert alert-error">{error}</div>}
          {success && <div className="alert alert-success">{success}</div>}
          
          <button className="btn btn-primary" onClick={handleSubmit} disabled={loading} style={{ width: '100%', maxWidth: '300px', height: '50px', fontSize: '1.1rem' }}>
            <Wand2 size={20} />
            릴스 자동 생성하기
          </button>
        </div>
      </div>

      {resultImg && (
        <div className="glass-panel" style={{ marginTop: '2rem', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
          <h2 style={{ marginBottom: '1.5rem' }}>생성된 릴스 결과</h2>
          
          <div style={{ display: 'flex', gap: '1rem', marginBottom: '1.5rem', flexWrap: 'wrap', justifyContent: 'center' }}>
             {videoUrl && (
                <a href={videoUrl} download="reels.mp4" className="btn btn-primary" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', background: '#e11d48', borderColor: '#e11d48' }}>
                  릴스 영상 다운로드 (MP4)
                </a>
             )}
          </div>
          
          {videoUrl && (
            <div style={{ marginBottom: '2rem', width: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
              <video src={videoUrl} controls autoPlay loop muted playsInline style={{ width: '100%', maxWidth: '400px', borderRadius: '16px', border: '1px solid var(--glass-border)' }} />
            </div>
          )}

          {resultPanels && resultPanels.length > 0 && (
            <div style={{ marginBottom: '2rem', width: '100%' }}>
              <h3 style={{ marginBottom: '1rem', textAlign: 'center', color: '#e2e8f0', fontSize: '1.1rem' }}>개별 이미지</h3>
              <div style={{ display: 'flex', gap: '1rem', overflowX: 'auto', paddingBottom: '1rem', justifyContent: 'center' }}>
                {resultPanels.map((panelUrl, idx) => (
                  <div key={idx} style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', alignItems: 'center', minWidth: '150px' }}>
                    <img src={panelUrl} alt={`컷 ${idx + 1}`} style={{ width: '150px', height: '266px', objectFit: 'cover', borderRadius: '8px', border: '1px solid var(--glass-border)' }} />
                    <a href={panelUrl} download={`card_${idx + 1}.jpg`} className="btn" style={{ padding: '0.5rem 1rem', fontSize: '0.8rem', background: 'rgba(255,255,255,0.05)', color: '#94a3b8', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.1)' }}>
                      다운로드
                    </a>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default Dashboard;
