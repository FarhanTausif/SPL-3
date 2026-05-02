/**
 * Advanced Animation Configurations
 * Framer Motion preset animations for consistent motion design
 */

import { Variants } from 'framer-motion'

/**
 * Entrance Animations
 */
export const fadeInUp: Variants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.4, ease: 'easeOut' },
  },
}

export const fadeInDown: Variants = {
  hidden: { opacity: 0, y: -20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.4, ease: 'easeOut' },
  },
}

export const slideInFromLeft: Variants = {
  hidden: { opacity: 0, x: -40 },
  visible: {
    opacity: 1,
    x: 0,
    transition: { duration: 0.4, ease: 'easeOut' },
  },
}

export const slideInFromRight: Variants = {
  hidden: { opacity: 0, x: 40 },
  visible: {
    opacity: 1,
    x: 0,
    transition: { duration: 0.4, ease: 'easeOut' },
  },
}

export const scaleIn: Variants = {
  hidden: { opacity: 0, scale: 0.8 },
  visible: {
    opacity: 1,
    scale: 1,
    transition: { duration: 0.4, ease: 'easeOut', type: 'spring', stiffness: 200 },
  },
}

export const zoomIn: Variants = {
  hidden: { opacity: 0, scale: 0.5 },
  visible: {
    opacity: 1,
    scale: 1,
    transition: { duration: 0.5, ease: 'easeOut', type: 'spring', damping: 15 },
  },
}

/**
 * Exit Animations
 */
export const fadeOutUp: Variants = {
  hidden: { opacity: 0 },
  exit: {
    opacity: 0,
    y: 20,
    transition: { duration: 0.3 },
  },
}

export const fadeOutDown: Variants = {
  hidden: { opacity: 0 },
  exit: {
    opacity: 0,
    y: -20,
    transition: { duration: 0.3 },
  },
}

/**
 * Hover/Focus Animations
 */
export const hoverScale = {
  whileHover: { scale: 1.05 },
  whileTap: { scale: 0.98 },
  transition: { type: 'spring', stiffness: 400, damping: 25 },
}

export const hoverGlow = {
  whileHover: {
    boxShadow: '0 20px 40px rgba(59, 130, 246, 0.3)',
  },
  transition: { duration: 0.3 },
}

/**
 * Stagger Container Animation
 * Use with AnimatePresence for list animations
 */
export const staggerContainer: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
      delayChildren: 0.2,
    },
  },
}

export const staggerItem: Variants = {
  hidden: { opacity: 0, y: 10 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.3 },
  },
}

/**
 * Skeleton Loading Animation
 */
export const shimmer: Variants = {
  animate: {
    backgroundPosition: ['200% 0', '-200% 0'],
    transition: {
      duration: 2,
      repeat: Infinity,
      repeatType: 'loop',
    },
  },
}

/**
 * Progress Bar Animation
 */
export const progressPulse: Variants = {
  animate: {
    opacity: [1, 0.7, 1],
    transition: {
      duration: 1.5,
      repeat: Infinity,
      repeatType: 'reverse',
    },
  },
}

/**
 * Status Badge Animations
 */
export const statusBadgeAnimation = {
  success: {
    scale: [1, 1.1, 1],
    transition: { duration: 0.4, times: [0, 0.5, 1] },
  },
  error: {
    x: [0, -5, 5, -5, 0],
    transition: { duration: 0.4 },
  },
  warning: {
    opacity: [1, 0.6, 1],
    transition: { duration: 0.5, repeat: Infinity },
  },
}

/**
 * Modal/Overlay Animations
 */
export const modalBackdrop: Variants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { duration: 0.2 } },
  exit: { opacity: 0, transition: { duration: 0.2 } },
}

export const modalContent: Variants = {
  hidden: { opacity: 0, scale: 0.95, y: 20 },
  visible: {
    opacity: 1,
    scale: 1,
    y: 0,
    transition: {
      type: 'spring',
      stiffness: 300,
      damping: 25,
    },
  },
  exit: {
    opacity: 0,
    scale: 0.95,
    y: 20,
    transition: { duration: 0.2 },
  },
}

/**
 * Tooltip Animation
 */
export const tooltipAnimation: Variants = {
  hidden: { opacity: 0, y: -8, scale: 0.95 },
  visible: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { duration: 0.2 },
  },
  exit: { opacity: 0, y: -8, scale: 0.95, transition: { duration: 0.15 } },
}

/**
 * Pulsing Animation
 */
export const pulseAnimation: Variants = {
  animate: {
    opacity: [1, 0.5, 1],
    transition: {
      duration: 2,
      repeat: Infinity,
      ease: 'easeInOut',
    },
  },
}

/**
 * Bounce Animation
 */
export const bounceAnimation: Variants = {
  animate: {
    y: [0, -10, 0],
    transition: {
      duration: 1,
      repeat: Infinity,
      ease: 'easeInOut',
    },
  },
}

/**
 * Rotation Animation
 */
export const rotationAnimation: Variants = {
  animate: {
    rotate: 360,
    transition: {
      duration: 2,
      repeat: Infinity,
      ease: 'linear',
    },
  },
}

/**
 * Combined Animations
 */
export const spin360: Variants = {
  animate: {
    rotate: 360,
    transition: { duration: 1, repeat: Infinity, ease: 'linear' },
  },
}

export const wiggle: Variants = {
  animate: {
    rotate: [-2, 2, -2, 2, -2],
    transition: { duration: 0.5, repeat: Infinity },
  },
}

export const float: Variants = {
  animate: {
    y: [0, -10, 0],
    transition: { duration: 3, repeat: Infinity, ease: 'easeInOut' },
  },
}

/**
 * Container for staggered animations
 */
export const createStaggerContainer = (delayChildren = 0.1): Variants => ({
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: delayChildren,
      delayChildren,
    },
  },
})
