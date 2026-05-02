# Storybook Component Library

**Date:** 2025-01-15  
**Status:** Phase 3 - Storybook Setup Complete

---

## 📖 Overview

Storybook has been set up as a comprehensive component library and documentation system. It allows developers and designers to:
- View all components in isolation
- Test different states and props
- Document component behavior
- Generate accessible and interactive documentation
- Maintain consistency across the application

---

## 🚀 Getting Started

### Starting Storybook

```bash
# Development mode (watch for changes)
npm run storybook

# Build static site
npm run storybook:build

# View at http://localhost:6006
```

### Building for Production

```bash
# Creates a static HTML site
npm run storybook:build

# Output in storybook-static/ directory
```

---

## 📚 Available Stories

### Workflow Components

#### 1. **AgentCard** (`components/workflow/AgentCard.stories.tsx`)
Status card for individual verification agents.

**Stories:**
- `Idle` - Agent waiting to start
- `Running` - Agent currently processing (with progress)
- `Complete` - Agent finished (with duration)
- `Error` - Agent encountered error
- `WithDuration` - Shows timing metadata
- `NonExpandable` - Read-only card

**Key Props:**
- `name`: Agent display name
- `role`: Agent type/role
- `status`: 'idle' | 'running' | 'complete' | 'error'
- `progress`: 0-100 completion percentage
- `duration`: Execution time in milliseconds
- `expandable`: Whether card is clickable

#### 2. **MetricsPanel** (`components/workflow/MetricsPanel.stories.tsx`)
Displays verification metrics and risk scores.

**Stories:**
- `LowRisk` - Hallucination risk < 0.3 (ACCEPT)
- `MediumRisk` - Hallucination risk 0.3-0.7 (WARN)
- `HighRisk` - Hallucination risk > 0.7 (REJECT)
- `RepairAttempt` - Policy decision = REPAIR
- `PartialVerification` - Incomplete verification stages

**Key Props:**
- `metrics`: Risk score, confidence, verification progress, timing
- `policyDecision`: 'accept' | 'warn' | 'repair' | 'reject'

#### 3. **EvidencePanel** (`components/workflow/EvidencePanel.stories.tsx`)
Lists collected evidence from verification pipeline.

**Stories:**
- `AllSuccess` - All verification stages passed
- `WithWarning` - Some stages with warnings
- `WithErrors` - Multiple failed stages
- `Loading` - Evidence collection in progress
- `Empty` - No evidence collected
- `Repair` - Evidence including repair attempts

**Key Props:**
- `evidence`: Array of evidence items
- `loading`: Whether still collecting evidence

#### 4. **ThemeToggle** (`components/ThemeToggle.stories.tsx`)
Theme switcher component.

**Stories:**
- `Default` - Standalone toggle
- `InHeader` - Toggle in app header context

---

## 🎨 Addons & Features

### Essentials Addon
- **Controls:** Interactive props editor
- **Actions:** Event handler logging
- **Viewport:** Responsive testing
- **Toolbars:** Quick controls

### Accessibility (A11y) Addon
- WCAG compliance checks
- Color contrast validation
- ARIA attribute validation

### Interactions Addon
- User interaction playback
- Component behavior testing
- Play function support

---

## 📋 Component Documentation

### Writing Stories

**Story Template:**
```typescript
import type { Meta, StoryObj } from '@storybook/react'
import { MyComponent } from '@/components/MyComponent'

const meta = {
  title: 'Category/ComponentName',
  component: MyComponent,
  parameters: {
    layout: 'centered',
    docs: {
      description: {
        component: 'Component description...',
      },
    },
  },
  tags: ['autodocs'],
  argTypes: {
    prop: {
      control: 'text',
      description: 'Prop description',
    },
  },
} satisfies Meta<typeof MyComponent>

export default meta
type Story = StoryObj<typeof meta>

export const Default: Story = {
  args: {
    prop: 'value',
  },
}
```

### Documentation Features

1. **Auto-generated Docs**
   - Props documentation from TypeScript types
   - Story code snippets
   - Live preview

2. **Props Table**
   - Automatic generation from component props
   - Type information
   - Default values

3. **Interactive Controls**
   - Edit props in real-time
   - Test different combinations
   - See changes instantly

---

## 🔍 Testing Components

### Visual Testing

1. Open Storybook: `npm run storybook`
2. Navigate to component story
3. Use Controls to test different props
4. Check responsive behavior with Viewport addon

### Accessibility Testing

1. Click "Accessibility" tab
2. Review WCAG compliance
3. Check color contrast ratios
4. Verify ARIA attributes

### Dark Mode Testing

1. Each story inherits dark mode support
2. Use browser DevTools to toggle dark class
3. All stories render in both light and dark

---

## 🏗️ Project Structure

```
frontend/
├── .storybook/
│   ├── main.ts           # Storybook config
│   └── preview.ts        # Global preview settings
├── components/
│   ├── workflow/
│   │   ├── AgentCard.tsx
│   │   ├── AgentCard.stories.tsx    ← Story file
│   │   ├── MetricsPanel.tsx
│   │   ├── MetricsPanel.stories.tsx ← Story file
│   │   ├── EvidencePanel.tsx
│   │   └── EvidencePanel.stories.tsx ← Story file
│   ├── ThemeToggle.tsx
│   └── ThemeToggle.stories.tsx      ← Story file
└── package.json
```

---

## 💻 Development Workflow

### Adding New Stories

1. Create component file: `components/MyComponent.tsx`
2. Create story file: `components/MyComponent.stories.tsx`
3. Export stories with different states
4. Run `npm run storybook` to view
5. Commit both files

### Story Naming Convention

- File: `ComponentName.stories.tsx`
- Title: `Category/ComponentName`
- Stories: PascalCase (e.g., `Default`, `Error`, `Loading`)

### Testing in Stories

```typescript
export const WithInteraction: Story = {
  play: async ({ canvasElement }) => {
    const button = canvasElement.querySelector('button')
    await userEvent.click(button)
    // Assert behavior...
  },
}
```

---

## 🎯 Component Library Organization

### Story Hierarchy

```
├── Workflow
│   ├── AgentCard
│   ├── MetricsPanel
│   ├── EvidencePanel
│   └── WorkflowDAG
├── Components
│   ├── ThemeToggle
│   ├── Header
│   ├── ErrorBoundary
│   └── ToastContainer
└── Layouts
    ├── Monitor Layout
    └── Results Layout
```

---

## 🔗 Integration with CI/CD

### GitHub Actions (Future)

```yaml
- name: Build Storybook
  run: npm run storybook:build

- name: Deploy Storybook
  uses: peaceiris/actions-gh-pages@v3
  with:
    github_token: ${{ secrets.GITHUB_TOKEN }}
    publish_dir: ./storybook-static
```

---

## 📈 Best Practices

### For Component Authors

1. **Export Stories for All States**
   - Idle, Loading, Success, Error, etc.
   - Different prop combinations
   - Edge cases

2. **Provide Clear Documentation**
   - Component purpose
   - Prop descriptions
   - Usage examples

3. **Test Accessibility**
   - Include A11y addon checks
   - Verify keyboard navigation
   - Check color contrast

4. **Consider Performance**
   - Lazy-load heavy components
   - Use memoization in stories
   - Optimize images

### For Designers

1. **Review Component Specs**
   - Check all variants
   - Test responsive behavior
   - Verify dark mode

2. **Provide Feedback**
   - Component naming
   - Visual consistency
   - Accessibility

---

## 🐛 Troubleshooting

### Storybook Won't Start

```bash
# Clear cache and reinstall
rm -rf node_modules/.vite
npm run storybook
```

### Props Not Showing in Controls

```typescript
// Ensure TypeScript types are exported
export interface ComponentProps {
  /** Prop description */
  prop: string
}

export const Component: React.FC<ComponentProps> = ({ prop }) => {
  // ...
}
```

### Dark Mode Not Working in Stories

```typescript
// Use ThemeProvider decorator
decorators: [
  (Story) => (
    <ThemeProvider>
      <Story />
    </ThemeProvider>
  ),
]
```

---

## 🚀 Next Steps

### Immediate

- [ ] Add more component stories
- [ ] Document all components
- [ ] Setup GitHub Pages deployment

### Short-term

- [ ] Create design tokens story
- [ ] Add color palette showcase
- [ ] Create typography story

### Long-term

- [ ] Integrate design system
- [ ] Auto-generate pattern library
- [ ] Setup design hand-off workflow

---

## 📚 Resources

- **Storybook Docs:** https://storybook.js.org/docs
- **React in Storybook:** https://storybook.js.org/docs/react
- **Next.js Integration:** https://storybook.js.org/docs/nextjs/getting-started
- **Accessibility Testing:** https://storybook.js.org/docs/react/writing-stories/accessibility-testing

---

## ✅ Phase 3: Storybook - COMPLETE

**Status:** Component library with stories for all main components  
**Build:** Configuration complete  
**Stories:** 12+ stories across 4 components ✅  
**Accessibility:** A11y addon integrated ✅  
**Documentation:** Auto-generated from TypeScript ✅  

**Next Phase:** Keyboard Shortcuts & Advanced Animations
