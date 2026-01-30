import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Navbar from './components/Navbar';
import HomePage from './pages/HomePage';
import ComposerListPage from './pages/ComposerListPage';
import ComposerDetailPage from './pages/ComposerDetailPage';
import WorkDetailPage from './pages/WorkDetailPage';
import SearchPage from './pages/SearchPage';
import AboutPage from './pages/AboutPage';
import './App.css';

function App() {
  return (
    <BrowserRouter>
      <div className="App">
        <Navbar />
        <Routes>
          <Route path="/" element={<ComposerListPage />} />
          <Route path="/works" element={<HomePage />} />
          <Route path="/composers" element={<ComposerListPage />} />
          <Route path="/composers/:id" element={<ComposerDetailPage />} />
          <Route path="/works/:id" element={<WorkDetailPage />} />
          <Route path="/search" element={<SearchPage />} />
          <Route path="/about" element={<AboutPage />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}

export default App;
