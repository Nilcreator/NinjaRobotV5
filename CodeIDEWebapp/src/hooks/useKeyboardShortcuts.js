import { useEffect } from 'react';

export function useKeyboardShortcuts({
    onSave,
    onUndo,
    onRedo,
    onRun
}) {
    useEffect(() => {
        const handleKeyDown = (e) => {
            // Check for Cmd (Mac) or Ctrl (Windows/Linux)
            const isCtrl = e.metaKey || e.ctrlKey;

            if (isCtrl) {
                switch (e.key.toLowerCase()) {
                    case 's':
                        e.preventDefault();
                        onSave();
                        break;
                    case 'z':
                        e.preventDefault();
                        if (e.shiftKey) {
                            onRedo();
                        } else {
                            onUndo();
                        }
                        break;
                    case 'enter':
                        e.preventDefault();
                        onRun();
                        break;
                    default:
                        break;
                }
            }
        };

        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [onSave, onUndo, onRedo, onRun]);
}

export default useKeyboardShortcuts;
