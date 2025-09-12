import Header from './Components/Header';
import './App.css';
import ChatPage from './Pages/ChatPage';
import LandinPage from './Pages/LandinPage';
import { Routes, Route, useLocation } from 'react-router-dom';

function App() {
  const location = useLocation();
  const path = location.pathname;

  const showHeader = path === '/ChatPage';

  return (
    <div className="App">
      {showHeader && <Header />}
      <Routes>
        <Route path="/" element={<LandinPage />} />
        <Route path="/ChatPage" element={<ChatPage />} />
      </Routes>
    </div>
  );
}

export default App;
