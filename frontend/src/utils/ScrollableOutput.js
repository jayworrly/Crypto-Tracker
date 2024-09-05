import React, { useEffect, useRef } from 'react';
import './ScrollableOutput.css';

function ScrollableOutput({ content }) {
    const containerRef = useRef(null);

    useEffect(() => {
        if (containerRef.current) {
            containerRef.current.scrollTop = containerRef.current.scrollHeight;
        }
    }, [content]);

    return (
        <div 
            className="scrollable-output"
            ref={containerRef}
        >
            <pre>{content}</pre>
        </div>
    );
}

export default ScrollableOutput;
