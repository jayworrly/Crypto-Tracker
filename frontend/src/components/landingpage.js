import React from 'react';
import { useNavigate } from 'react-router-dom';
import './landingpage.css'; // Optional: Create a CSS file for styling

function LandingPage() {
    const navigate = useNavigate();

    const handleClick = () => {
        navigate('/dashboard');
    };

    return (
        <div className="landing-page" onClick={handleClick}>
            <h1>Welcome to Jayworrly's Analytic Page</h1>
            <p>Sharing Data from DEXs Transactions.</p>
        </div>
    );
}

export default LandingPage;
