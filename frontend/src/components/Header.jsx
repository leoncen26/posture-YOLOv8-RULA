/**
 * Header Component
 * 
 * Purpose:
 * Displays the main title and subtitle of the Posture Analysis System.
 * This component provides the application branding and brief description.
 * 
 * Props: None
 * 
 * @returns {JSX.Element} The rendered header section
 */

const Header = () => {
  return (
    <header className="text-center mb-8">
      {/* Main Title */}
      <h1 className="text-4xl font-bold text-gray-800 mb-2!">
        Posture Analysis System
      </h1>
      
      {/* Subtitle/Description */}
      <p className="text-lg text-gray-500">
        Analyze table manner posture in real-time
      </p>
    </header>
  );
};

export default Header;
