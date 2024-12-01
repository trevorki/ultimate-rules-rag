import React from 'react';



export const TypingDots = () => {

  return (

    <div className="flex space-x-1 items-center p-1">

      <div className="w-1.5 h-1.5 rounded-full bg-current animate-typing-dot"></div>

      <div className="w-1.5 h-1.5 rounded-full bg-current animate-typing-dot [animation-delay:0.2s]"></div>

      <div className="w-1.5 h-1.5 rounded-full bg-current animate-typing-dot [animation-delay:0.4s]"></div>

    </div>

  );

};
