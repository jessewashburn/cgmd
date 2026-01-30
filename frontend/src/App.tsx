import { BrowserRouter, Routes, Route } from 'react-router-dom';
import HomePage from './pages/HomePage';
import ComposerListPage from './pages/ComposerListPage';
import ComposerDetailPage from './pages/ComposerDetailPage';
import WorkDetailPage from './pages/WorkDetailPage';
import SearchPage from './pages/SearchPage';
import './App.css';

function App() {
  return (
    <BrowserRouter>
      <div className="App">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/composers" element={<ComposerListPage />} />
          <Route path="/composers/:id" element={<ComposerDetailPage />} />
          <Route path="/works/:id" element={<WorkDetailPage />} />
          <Route path="/search" element={<SearchPage />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}

export default App;
