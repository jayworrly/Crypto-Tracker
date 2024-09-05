import React from 'react';
import ScrollableOutput from './ScrollableOutput';

function withScrollableOutput(WrappedComponent) {
  return function WithScrollableOutput(props) {
    return (
      <WrappedComponent
        {...props}
        ScrollableOutput={ScrollableOutput}
      />
    );
  };
}

export default withScrollableOutput;
