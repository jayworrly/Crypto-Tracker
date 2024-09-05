import React from 'react';
import { Link } from 'react-router-dom';
import './dashboard.css'; // Optional: Create a CSS file for styling

function Dashboard() {
    return (
        <div className="dashboard">
            <h1>Jayworrly's Analytics Dashboard</h1>
            <p>Welcome to the Jayworrly's Tracker!</p>
            <p>Select a category to explore:</p>
            
            {/* Navigation Bar */}
            <nav className="nav-bar">
                <Link to="/avalanche" className="nav-item" style={{ pointerEvents: 'auto' }}>Avalanche</Link>
                <Link to="/solana" className="nav-item" style={{ pointerEvents: 'auto' }}>Solana</Link>
            </nav>
        </div>
    );
}

export default Dashboard;
