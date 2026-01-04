import { useState } from 'react';
import * as Blockly from 'blockly';

const STORAGE_KEY_PREFIX = 'ninjarobot_proj_';

export function useProject(workspaceRef) {
    // Lazy initialization for synchronous localStorage
    const [projectNames, setProjectNames] = useState(() => {
        const names = [];
        if (typeof localStorage === 'undefined') return [];

        for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i);
            if (key.startsWith(STORAGE_KEY_PREFIX)) {
                names.push(key.replace(STORAGE_KEY_PREFIX, ''));
            }
        }
        return names.sort();
    });

    const refreshProjectList = () => {
        const names = [];
        for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i);
            if (key.startsWith(STORAGE_KEY_PREFIX)) {
                names.push(key.replace(STORAGE_KEY_PREFIX, ''));
            }
        }
        setProjectNames(names.sort());
    };

    const saveProject = (name) => {
        if (!workspaceRef.current) return;

        const xml = Blockly.Xml.workspaceToDom(workspaceRef.current);
        const xmlText = Blockly.Xml.domToText(xml);

        localStorage.setItem(STORAGE_KEY_PREFIX + name, xmlText);
        refreshProjectList();
        return true;
    };

    const loadProject = (name) => {
        if (!workspaceRef.current) return;

        const xmlText = localStorage.getItem(STORAGE_KEY_PREFIX + name);
        if (!xmlText) return false;

        try {
            const xml = Blockly.utils.xml.textToDom(xmlText);
            workspaceRef.current.clear();
            Blockly.Xml.domToWorkspace(xml, workspaceRef.current);
            return true;
        } catch (e) {
            console.error('Failed to load project:', e);
            return false;
        }
    };

    const deleteProject = (name) => {
        localStorage.removeItem(STORAGE_KEY_PREFIX + name);
        refreshProjectList();
    };

    return {
        projectNames,
        saveProject,
        loadProject,
        deleteProject
    };
}

export default useProject;
