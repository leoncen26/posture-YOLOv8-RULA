# Frontend Architecture Documentation

## Overview
This document describes the clean architecture and component structure of the Posture Analysis System frontend.

## Project Structure

```
frontend/
├── src/
│   ├── components/          # Reusable UI components
│   │   ├── Header.jsx      # Application title and subtitle
│   │   ├── VideoPanel.jsx  # Individual video display panel
│   │   ├── VideoDisplay.jsx # Container for dual video panels
│   │   ├── ControlButton.jsx # Webcam control button
│   │   ├── HelpButton.jsx  # Help/info button
│   │   └── HelpModal.jsx   # Help information modal
│   │
│   ├── hooks/              # Custom React hooks
│   │   └── useWebcam.js    # Webcam management hook
│   │
│   ├── App.jsx             # Main application component
│   ├── App.css             # App-specific styles
│   ├── index.css           # Global styles
│   └── main.jsx            # Application entry point
│
├── public/                 # Static assets
├── package.json           # Dependencies and scripts
└── vite.config.js         # Vite configuration
```

## Component Architecture

### 1. **App.jsx** (Main Container)
- **Purpose**: Root component that orchestrates the entire application
- **Responsibilities**:
  - Manages global state (webcam, modals)
  - Composes all major UI components
  - Handles error display
  - Provides application layout

### 2. **Components**

#### **Header.jsx**
- **Purpose**: Display application title and description
- **Props**: None
- **State**: None
- **Styling**: Tailwind utility classes

#### **VideoPanel.jsx**
- **Purpose**: Reusable video display component for individual camera feeds
- **Props**:
  - `view` (string): 'front' or 'side'
  - `videoStream` (MediaStream): Video stream object
  - `isActive` (boolean): Camera active state
- **Features**:
  - Displays placeholder when inactive
  - Shows live video feed when active
  - Canvas overlay for pose detection visualization
  - View label indicator

#### **VideoDisplay.jsx**
- **Purpose**: Container for both front and side video panels
- **Props**:
  - `videoStream` (MediaStream): Video stream to pass to panels
  - `isActive` (boolean): Camera active state
- **Layout**: Responsive flex layout for dual panels

#### **ControlButton.jsx**
- **Purpose**: Button to toggle webcam on/off
- **Props**:
  - `isActive` (boolean): Current webcam state
  - `onClick` (function): Click handler
  - `isLoading` (boolean): Loading state
- **Features**:
  - Dynamic text based on state
  - Visual feedback for different states
  - Disabled state during loading
  - Icon changes based on state

#### **HelpButton.jsx**
- **Purpose**: Fixed position help button
- **Props**:
  - `onClick` (function): Click handler to open help modal
- **Styling**: Fixed positioning in top-right corner

#### **HelpModal.jsx**
- **Purpose**: Display help information and usage instructions
- **Props**:
  - `isOpen` (boolean): Modal visibility state
  - `onClose` (function): Handler to close modal
- **Features**:
  - Backdrop overlay
  - Scrollable content
  - Organized sections (What, How, Tips, Privacy)
  - Close button and click-outside-to-close

### 3. **Custom Hooks**

#### **useWebcam.js**
- **Purpose**: Encapsulate webcam logic and state management
- **Returns**:
  - `videoStream`: Current MediaStream object
  - `isActive`: Whether webcam is on
  - `isLoading`: Whether webcam is initializing
  - `error`: Error message if any
  - `toggleWebcam`: Function to start/stop webcam
  - `stopWebcam`: Function to explicitly stop webcam
- **Features**:
  - Browser permission handling
  - Error state management
  - Cleanup on unmount
  - Optimal video constraints

## Design Principles

### 1. **Clean Architecture**
- **Separation of Concerns**: Each component has a single, well-defined purpose
- **Reusability**: Components like `VideoPanel` are designed to be reused
- **Modularity**: Easy to add, remove, or modify components independently

### 2. **Component Composition**
- Parent components compose child components
- Data flows down via props
- Events flow up via callbacks
- Clear component hierarchy

### 3. **State Management**
- **Local State**: Component-specific state (e.g., modal open/close)
- **Lifted State**: Shared state in parent component (e.g., webcam state)
- **Custom Hooks**: Encapsulate complex logic (e.g., webcam management)

### 4. **Styling Strategy**
- **Tailwind CSS**: Utility-first approach for rapid development
- **Custom CSS**: Component-specific styles in App.css
- **Global Styles**: Base styles in index.css
- **Responsive Design**: Mobile-first approach with responsive utilities

### 5. **Code Quality**
- **Comments**: Comprehensive JSDoc-style comments for all components
- **Naming**: Clear, descriptive names for variables and functions
- **Structure**: Consistent file and code structure
- **Documentation**: Inline explanations for complex logic

## Styling System

### Tailwind CSS Classes Used
- **Layout**: `flex`, `grid`, `container`, `mx-auto`
- **Spacing**: `p-*`, `m-*`, `gap-*`
- **Typography**: `text-*`, `font-*`
- **Colors**: `bg-*`, `text-*`, `border-*`
- **Effects**: `shadow-*`, `rounded-*`, `hover:*`, `transition-*`
- **Responsive**: `sm:*`, `md:*`, `lg:*`

### Custom CSS
- Video mirroring effect
- Custom animations (fade-in, pulse, spin)
- Focus states for accessibility
- Responsive video panel heights

## Future Enhancements

### Planned Features
1. **Real-time RULA Score Display**: Show posture assessment scores
2. **Historical Data**: Track posture over time
3. **Notifications**: Alert users about poor posture
4. **Settings Panel**: Customize analysis parameters
5. **Export Reports**: Generate posture analysis reports

### Technical Improvements
1. **Testing**: Add unit and integration tests
2. **Error Boundary**: Implement React error boundaries
3. **Performance**: Optimize video processing
4. **Accessibility**: Enhanced ARIA labels and keyboard navigation
5. **Internationalization**: Multi-language support

## Getting Started

### Installation
```bash
cd frontend
npm install
```

### Development
```bash
npm run dev
```

### Build
```bash
npm run build
```

### Preview Production Build
```bash
npm run preview
```

## Browser Compatibility
- Chrome/Edge: ✅ Full support
- Firefox: ✅ Full support
- Safari: ✅ Full support (iOS 14.3+)
- Opera: ✅ Full support

## Dependencies
- **React**: ^19.2.0 - UI library
- **React DOM**: ^19.2.0 - React renderer
- **Tailwind CSS**: ^4.2.0 - Utility-first CSS framework
- **Vite**: ^7.3.1 - Build tool and dev server

## Contributing
When adding new components:
1. Follow the established file structure
2. Add comprehensive comments
3. Use consistent naming conventions
4. Implement responsive design
5. Update this documentation

---

**Last Updated**: February 22, 2026
**Version**: 1.0.0
