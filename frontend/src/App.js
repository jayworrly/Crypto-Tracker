import React from 'react';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import LandingPage from './components/landingpage';
import Dashboard from './components/dashboard';
import Avalanche from './components/avalanche';
import Solana from './components/solana';
import withScrollableOutput from './utils/withScrollableOutput';
import './App.css';

// Wrap the components that need ScrollableOutput with the HOC
const AvalancheWithScroll = withScrollableOutput(Avalanche);
const SolanaWithScroll = withScrollableOutput(Solana);

function App() {
  return (
    <Router>
      <div className="App">
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/avalanche" element={<AvalancheWithScroll />} />
          <Route path="/solana" element={<SolanaWithScroll />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
