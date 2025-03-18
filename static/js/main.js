/**
 * AI-Enhanced Notes Management System
 * Main JavaScript file for frontend functionality
 */

// Global state
const state = {
    notes: [],
    trashNotes: [],
    currentNote: null,
    analytics: null,
    toastInstance: null,
    notesByDateChart: null,
    searchQuery: '',
    tags: JSON.parse(localStorage.getItem('tags') || '[]'),
    cachedSummaries: JSON.parse(localStorage.getItem('summaries') || '{}')
};

// DOM Elements
const dom = {
    // Notes list
    notesList: document.getElementById('notesList'),
    trashList: document.getElementById('trashList'),
    trashCount: document.getElementById('trashCount'),
    searchInput: document.getElementById('searchInput'),
    notesContainer: document.getElementById('notesContainer'),
    
    // Note editor
    noteEditor: document.getElementById('noteEditor'),
    noteTitle: document.getElementById('noteTitle'),
    noteContent: document.getElementById('noteContent'),
    currentNoteId: document.getElementById('currentNoteId'),
    tagsContainer: document.getElementById('tagsContainer'),
    tagInput: document.getElementById('tagInput'),
    saveNoteBtn: document.getElementById('saveNoteBtn'),
    showVersionsBtn: document.getElementById('showVersionsBtn'),
    summarizeBtn: document.getElementById('summarizeBtn'),
    deleteNoteBtn: document.getElementById('deleteNoteBtn'),
    
    // Buttons
    newNoteBtn: document.getElementById('newNoteBtn'),
    
    // Summary card
    summaryCard: document.getElementById('summaryCard'),
    summaryContent: document.getElementById('summaryContent'),
    summaryLanguage: document.getElementById('summaryLanguage'),
    summaryTimestamp: document.getElementById('summaryTimestamp'),
    
    // Versions modal
    versionsModal: document.getElementById('versionsModal') 
        ? new bootstrap.Modal(document.getElementById('versionsModal')) 
        : null,
    versionsList: document.getElementById('versionsList'),
    
    // Analytics
    totalNotesCount: document.getElementById('totalNotesCount'),
    activeNotesCount: document.getElementById('activeNotesCount'),
    deletedNotesCount: document.getElementById('deletedNotesCount'),
    totalWordCount: document.getElementById('totalWordCount'),
    averageNoteLength: document.getElementById('averageNoteLength'),
    topWordsList: document.getElementById('topWordsList'),
    longestNotesList: document.getElementById('longestNotesList'),
    shortestNotesList: document.getElementById('shortestNotesList'),
    notesByDateChart: document.getElementById('notesByDateChart'),
    analyticsTimestamp: document.getElementById('analyticsTimestamp'),
    
    // Toast
    notificationToast: document.getElementById('notificationToast')
};

// Initialize toast
if (dom.notificationToast) {
    state.toastInstance = new bootstrap.Toast(dom.notificationToast);
}


// API Client
const api = {
    baseUrl: '/api',
    
    // Generic fetch with error handling
    async fetchJson(url, options = {}) {
        try {
            // Show loading spinner for longer operations
            if (options.showLoader) {
                document.body.classList.add('loading-active');
            }
            
            const response = await fetch(url, {
                ...options,
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                }
            });
            
            if (options.showLoader) {
                document.body.classList.remove('loading-active');
            }
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || `API Error: ${response.status}`);
            }
            
            // Handle 204 No Content responses (common for DELETE operations)
            if (response.status === 204) {
                return {};
            }
            
            // For other successful responses, parse JSON
            return await response.json();
        } catch (error) {
            if (options.showLoader) {
                document.body.classList.remove('loading-active');
            }
            console.error('API Error:', error);
            showNotification(error.message, 'danger');
            throw error;
        }
    },
    
    // Notes API
    notes: {
        getAll: (includeDeleted = false) => 
            api.fetchJson(`${api.baseUrl}/notes${includeDeleted ? '?include_deleted=true' : ''}`),
        getById: (id) => api.fetchJson(`${api.baseUrl}/notes/${id}`),
        search: (query) => api.fetchJson(`${api.baseUrl}/notes/search?q=${encodeURIComponent(query)}`),
        create: (data) => api.fetchJson(`${api.baseUrl}/notes`, {
            method: 'POST',
            body: JSON.stringify(data),
            showLoader: true
        }),
        update: (id, data) => api.fetchJson(`${api.baseUrl}/notes/${id}`, {
            method: 'PUT',
            body: JSON.stringify(data),
            showLoader: true
        }),
        delete: (id, permanent = false) => 
            api.fetchJson(`${api.baseUrl}/notes/${id}${permanent ? '?permanent=true' : ''}`, { 
                method: 'DELETE',
                showLoader: true
            }),
        getVersions: (id) => api.fetchJson(`${api.baseUrl}/notes/${id}/versions`, { showLoader: true }),
        restore: (id) => api.fetchJson(`${api.baseUrl}/notes/${id}/restore`, { 
            method: 'POST',
            showLoader: true
        })
    },
    
    // AI API
    ai: {
        summarize: (id, language = 'en') => 
            api.fetchJson(`${api.baseUrl}/ai/summarize/${id}?language=${language}`, { showLoader: true }),
        getSupportedLanguages: () => api.fetchJson(`${api.baseUrl}/ai/languages`)
    },
    
    // Analytics API
    analytics: {
        get: () => api.fetchJson(`${api.baseUrl}/analytics`, { showLoader: true }),
        getWordCloud: () => api.fetchJson(`${api.baseUrl}/analytics/word-cloud`),
        getTimeDistribution: () => api.fetchJson(`${api.baseUrl}/analytics/time-distribution`)
    }
};

// Show notification toast
function showNotification(message, type = 'primary') {
    if (!dom.notificationToast || !state.toastInstance) return;
    
    const toast = dom.notificationToast;
    
    // Set colors based on type
    toast.classList.remove('bg-primary', 'bg-success', 'bg-danger', 'bg-warning', 'bg-info');
    toast.classList.add(`bg-${type}`);
    
    if (['danger', 'warning', 'primary', 'dark'].includes(type)) {
        toast.classList.add('text-white');
    } else {
        toast.classList.remove('text-white');
    }
    
    // Set content
    toast.querySelector('.toast-header strong').textContent = 
        type === 'danger' ? 'Error' : 
        type === 'success' ? 'Success' : 
        type === 'warning' ? 'Warning' : 'Notification';
        
    toast.querySelector('.toast-body').textContent = message;
    
    // Show toast
    state.toastInstance.show();
}

// Format date for display
function formatDate(dateString) {
    if (!dateString) return 'Unknown date';
    
    const options = { 
        year: 'numeric', 
        month: 'short', 
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    };
    return new Date(dateString).toLocaleString(undefined, options);
}

// Count words in text
function countWords(text) {
    if (!text) return 0;
    return text.trim().split(/\s+/).filter(word => word.length > 0).length;
}

// Update word count display
function updateWordCount() {
    if (!dom.noteContent || !document.querySelector('.word-count')) return;
    
    const wordCount = countWords(dom.noteContent.value);
    document.querySelector('.word-count').textContent = `${wordCount} words`;
}

// Add tag to current note
function addTag(tagName) {
    if (!dom.tagsContainer) return;
    
    // Trim and validate
    tagName = tagName.trim();
    if (!tagName || tagName.length === 0) return;
    
    // Check if tag already exists
    const existingTags = Array.from(dom.tagsContainer.querySelectorAll('.tag'))
        .map(tag => tag.textContent.trim().replace('×', ''));
    
    if (existingTags.includes(tagName)) return;
    
    // Create tag element
    const tagElement = document.createElement('div');
    tagElement.className = 'tag fade-in';
    tagElement.innerHTML = `
        ${tagName}
        <span class="remove-tag">×</span>
    `;
    
    // Add delete handler
    tagElement.querySelector('.remove-tag').addEventListener('click', (e) => {
        e.stopPropagation();
        tagElement.classList.add('fade-out');
        setTimeout(() => {
            tagElement.remove();
        }, 300);
    });
    
    // Add to container
    dom.tagsContainer.appendChild(tagElement);
    
    // Add to global tags list if not already there
    if (!state.tags.includes(tagName)) {
        state.tags.push(tagName);
        localStorage.setItem('tags', JSON.stringify(state.tags));
        
        // Update datalist if it exists
        if (document.getElementById('tagSuggestions')) {
            const option = document.createElement('option');
            option.value = tagName;
            document.getElementById('tagSuggestions').appendChild(option);
        }
    }
    
    // Clear input
    if (dom.tagInput) {
        dom.tagInput.value = '';
        dom.tagInput.focus();
    }
}

// Load notes from API
async function loadNotes() {
    try {
        // Show loading state
        if (dom.notesContainer) {
            dom.notesContainer.classList.add('loading');
        }
        
        // Get all notes including deleted ones
        const response = await api.notes.getAll(true);
        
        // Update state
        state.notes = response.filter(note => !note.is_deleted);
        state.trashNotes = response.filter(note => note.is_deleted);
        
        // Apply search filter if needed
        if (state.searchQuery) {
            filterNotesBySearch();
        } else {
            // Render notes list
            renderNotesList();
        }
        
        renderTrashList();
        
        // Check for note limit
        if (state.notes.length >= 10) {
            showNotification('You have reached the limit of 10 notes. Delete some to create more.', 'warning');
            if (dom.newNoteBtn) dom.newNoteBtn.disabled = true;
        } else {
            if (dom.newNoteBtn) dom.newNoteBtn.disabled = false;
        }
        
        if (dom.notesContainer) {
            dom.notesContainer.classList.remove('loading');
        }
    } catch (error) {
        if (dom.notesContainer) {
            dom.notesContainer.classList.remove('loading');
        }
        console.error('Failed to load notes:', error);
        showNotification('Failed to load notes. Please try again.', 'danger');
    }
}

// Filter notes by search query
function filterNotesBySearch() {
    const query = state.searchQuery.toLowerCase();
    
    if (!query) {
        renderNotesList();
        return;
    }
    
    const filteredNotes = state.notes.filter(note => 
        note.title.toLowerCase().includes(query) || 
        note.content.toLowerCase().includes(query) ||
        (note.tags && note.tags.some(tag => tag.toLowerCase().includes(query)))
    );
    
    renderNotesList(filteredNotes);
}

// Handle search input
function handleSearchInput(e) {
    state.searchQuery = e.target.value;
    filterNotesBySearch();
}

// Render notes list
function renderNotesList(notesToRender = null) {
    // Use provided notes or all notes from state
    const notes = notesToRender || state.notes;
    
    if (!dom.notesList) return;
    
    if (notes.length === 0) {
        dom.notesList.innerHTML = `
            <li class="list-group-item text-center text-muted fade-in">
                ${state.searchQuery ? 'No matching notes found.' : 'No notes found. Create one!'}
            </li>
        `;
        return;
    }
    
    // Sort notes by updated date (newest first)
    const sortedNotes = [...notes].sort((a, b) => 
        new Date(b.updated_at) - new Date(a.updated_at)
    );
    
    // Create HTML
    const notesHtml = sortedNotes.map(note => {
        const tags = note.tags || [];
        const tagsHtml = tags.length > 0 
            ? `<div class="tags-container">
                ${tags.slice(0, 2).map(tag => `<span class="tag">${tag}</span>`).join('')}
                ${tags.length > 2 ? `<span class="tag">+${tags.length - 2}</span>` : ''}
               </div>` 
            : '';
            
        return `
            <li class="list-group-item ${state.currentNote && note.id === state.currentNote.id ? 'active' : ''} fade-in" 
                data-note-id="${note.id}">
                <div class="note-item">
                    <div class="note-title-container">
                        <span class="note-title">${note.title}</span>
                        ${tagsHtml}
                    </div>
                    <small class="note-date">${formatDate(note.updated_at)}</small>
                </div>
            </li>
        `;
    }).join('');
    
    dom.notesList.innerHTML = notesHtml;
    
    // Add event listeners
    dom.notesList.querySelectorAll('.list-group-item').forEach(item => {
        item.addEventListener('click', () => loadNote(parseInt(item.dataset.noteId)));
    });
}

// Render trash list
function renderTrashList() {
    if (!dom.trashList || !dom.trashCount) return;
    
    dom.trashCount.textContent = state.trashNotes.length;
    
    if (state.trashNotes.length === 0) {
        dom.trashList.innerHTML = `
            <li class="list-group-item text-center text-muted fade-in">
                No deleted notes
            </li>
        `;
        return;
    }
    
    // Sort by delete date (newest first)
    const sortedTrash = [...state.trashNotes].sort((a, b) => 
        new Date(b.deleted_at) - new Date(a.deleted_at)
    );
    
    // Create HTML
    const trashHtml = sortedTrash.map(note => `
        <li class="list-group-item fade-in" data-note-id="${note.id}">
            <div class="d-flex justify-content-between align-items-center">
                <span class="note-title">${note.title}</span>
                <div class="action-icons">
                    <button class="btn btn-sm btn-outline-success restore-note" 
                        data-note-id="${note.id}" title="Restore">
                        <i class="fas fa-trash-restore"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-danger delete-permanent" 
                        data-note-id="${note.id}" title="Delete Permanently">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            </div>
            <small class="text-muted">Deleted: ${formatDate(note.deleted_at)}</small>
        </li>
    `).join('');
    
    dom.trashList.innerHTML = trashHtml;
    
    // Add event listeners
    dom.trashList.querySelectorAll('.restore-note').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            e.stopPropagation();
            const noteId = parseInt(btn.dataset.noteId);
            await restoreNote(noteId);
        });
    });
    
    dom.trashList.querySelectorAll('.delete-permanent').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            e.stopPropagation();
            const noteId = parseInt(btn.dataset.noteId);
            
            if (confirm('Permanently delete this note? This cannot be undone.')) {
                await deleteNote(noteId, true);
            }
        });
    });
}

// Load a specific note
async function loadNote(noteId) {
    try {
        if (!dom.noteTitle || !dom.noteContent) return;
        
        if (dom.noteEditor) {
            dom.noteEditor.classList.add('loading');
        }
        
        const note = await api.notes.getById(noteId);
        
        // Update state
        state.currentNote = note;
        
        // Update UI
        dom.noteTitle.value = note.title;
        dom.noteContent.value = note.content;
        dom.currentNoteId.value = note.id;
        
        // Update tags if container exists
        if (dom.tagsContainer) {
            dom.tagsContainer.innerHTML = '';
            if (note.tags && Array.isArray(note.tags)) {
                note.tags.forEach(tag => {
                    const tagElement = document.createElement('div');
                    tagElement.className = 'tag';
                    tagElement.innerHTML = `
                        ${tag}
                        <span class="remove-tag">×</span>
                    `;
                    
                    // Add delete handler
                    tagElement.querySelector('.remove-tag').addEventListener('click', (e) => {
                        e.stopPropagation();
                        tagElement.classList.add('fade-out');
                        setTimeout(() => {
                            tagElement.remove();
                        }, 300);
                    });
                    
                    dom.tagsContainer.appendChild(tagElement);
                });
            }
        }
        
        // Update word count
        updateWordCount();
        
        // Enable buttons
        if (dom.showVersionsBtn) dom.showVersionsBtn.disabled = false;
        if (dom.summarizeBtn) dom.summarizeBtn.disabled = false;
        if (dom.deleteNoteBtn) dom.deleteNoteBtn.disabled = false;
        
        // Check if we have a cached summary and show it
        const cachedSummary = state.cachedSummaries[noteId];
        if (cachedSummary && dom.summaryCard) {
            dom.summaryContent.innerHTML = `<p class="lead">${cachedSummary.summary}</p>`;
            dom.summaryTimestamp.textContent = formatDate(cachedSummary.generated_at);
            dom.summaryCard.style.display = 'block';
        } else if (dom.summaryCard) {
            dom.summaryCard.style.display = 'none';
        }
        
        // Update list highlighting
        renderNotesList();
        
        if (dom.noteEditor) {
            dom.noteEditor.classList.remove('loading');
        }
    } catch (error) {
        if (dom.noteEditor) {
            dom.noteEditor.classList.remove('loading');
        }
        console.error('Failed to load note:', error);
        showNotification('Failed to load note: ' + error.message, 'danger');
    }
}

// Create a new note
async function createNote() {
    // Check for note limit
    if (state.notes.length >= 10) {
        showNotification('You have reached the limit of 10 notes. Delete some to create more.', 'warning');
        return;
    }
    
    try {
        // Reset form
        if (dom.noteTitle) dom.noteTitle.value = '';
        if (dom.noteContent) dom.noteContent.value = '';
        if (dom.currentNoteId) dom.currentNoteId.value = '';
        state.currentNote = null;
        
        // Clear tags if tags container exists
        if (dom.tagsContainer) {
            dom.tagsContainer.innerHTML = '';
        }
        
        // Update word count
        updateWordCount();
        
        // Disable buttons
        if (dom.showVersionsBtn) dom.showVersionsBtn.disabled = true;
        if (dom.summarizeBtn) dom.summarizeBtn.disabled = true;
        if (dom.deleteNoteBtn) dom.deleteNoteBtn.disabled = true;
        
        // Hide summary card
        if (dom.summaryCard) dom.summaryCard.style.display = 'none';
        
        // Set focus on title
        if (dom.noteTitle) dom.noteTitle.focus();
        
        // Update list highlighting
        renderNotesList();
        
        showNotification('Create a new note', 'info');
    } catch (error) {
        console.error('Failed to create note:', error);
        showNotification('Failed to create note', 'danger');
    }
}

// Save the current note
async function saveNote() {
    if (!dom.noteTitle || !dom.noteContent) return;
    
    const title = dom.noteTitle.value.trim();
    const content = dom.noteContent.value.trim();
    const noteId = dom.currentNoteId.value;
    
    if (!title) {
        showNotification('Please enter a title for your note', 'warning');
        dom.noteTitle.focus();
        return;
    }
    
    if (!content) {
        showNotification('Please enter some content for your note', 'warning');
        dom.noteContent.focus();
        return;
    }
    
    try {
        // Get tags if tags container exists
        let tags = [];
        if (dom.tagsContainer) {
            tags = Array.from(dom.tagsContainer.querySelectorAll('.tag')).map(tag => 
                tag.textContent.trim().replace('×', '')
            );
        }
        
        // Show loading state
        if (dom.noteEditor) {
            dom.noteEditor.classList.add('loading');
        }
        
        let savedNote;
        
        if (noteId) {
            // Update existing note
            savedNote = await api.notes.update(noteId, { title, content, tags });
            showNotification('Note updated successfully', 'success');
        } else {
            // Create new note
            savedNote = await api.notes.create({ title, content, tags });
            showNotification('Note created successfully', 'success');
        }
        
        // Update state
        state.currentNote = savedNote;
        dom.currentNoteId.value = savedNote.id;
        
        // Enable buttons
        if (dom.showVersionsBtn) dom.showVersionsBtn.disabled = false;
        if (dom.summarizeBtn) dom.summarizeBtn.disabled = false;
        if (dom.deleteNoteBtn) dom.deleteNoteBtn.disabled = false;
        
        // Remove loading state
        if (dom.noteEditor) {
            dom.noteEditor.classList.remove('loading');
        }
        
        // Refresh notes list
        await loadNotes();
        
        // Load analytics
        loadAnalytics();
        
    } catch (error) {
        if (dom.noteEditor) {
            dom.noteEditor.classList.remove('loading');
        }
        console.error('Failed to save note:', error);
        showNotification('Failed to save note: ' + error.message, 'danger');
    }
}

// Delete a note
async function deleteNote(noteId, permanent = false) {
    console.log('deleteNote function called with:', { noteId, permanent });
    
    try {
        console.log('Calling API delete endpoint');
        const result = await api.notes.delete(noteId, permanent);
        console.log('Delete API response:', result);
        
        // Show notification
        if (permanent) {
            showNotification('Note permanently deleted', 'info');
        } else {
            showNotification('Note moved to trash', 'info');
        }
        
        // Clear editor if current note was deleted
        if (state.currentNote && state.currentNote.id === noteId) {
            state.currentNote = null;
            if (dom.noteTitle) dom.noteTitle.value = '';
            if (dom.noteContent) dom.noteContent.value = '';
            if (dom.currentNoteId) dom.currentNoteId.value = '';
            if (dom.showVersionsBtn) dom.showVersionsBtn.disabled = true;
            if (dom.summarizeBtn) dom.summarizeBtn.disabled = true;
            if (dom.deleteNoteBtn) dom.deleteNoteBtn.disabled = true;
            if (dom.summaryCard) dom.summaryCard.style.display = 'none';
            if (dom.tagsContainer) dom.tagsContainer.innerHTML = '';
            updateWordCount();
        }
        
        // Refresh notes list
        await loadNotes();
        
        // Load analytics
        loadAnalytics();
        
    } catch (error) {
        console.error('Failed to delete note:', error);
        showNotification('Failed to delete note: ' + error.message, 'danger');
    }
}

// Restore a note from trash
async function restoreNote(noteId) {
    try {
        await api.notes.restore(noteId);
        
        // Show notification
        showNotification('Note restored successfully', 'success');
        
        // Refresh notes list
        await loadNotes();
        
        // Load analytics
        loadAnalytics();
        
    } catch (error) {
        console.error('Failed to restore note:', error);
        showNotification('Failed to restore note: ' + error.message, 'danger');
    }
}

// Show version history
async function showVersionHistory(noteId) {
    if (!dom.versionsList || !dom.versionsModal) return;
    
    try {
        // Show loading state
        dom.versionsList.innerHTML = `
            <div class="list-group-item text-center p-4">
                <span class="loading"></span>
                <p class="mt-3">Loading version history...</p>
            </div>
        `;
        
        // Show the modal first so the loading spinner is visible
        dom.versionsModal.show();
        
        const versions = await api.notes.getVersions(noteId);
        
        if (Object.keys(versions).length === 0) {
            dom.versionsList.innerHTML = `
                <div class="list-group-item text-center text-muted p-4">
                    <i class="fas fa-history fa-3x mb-3 text-muted"></i>
                    <p>No version history available</p>
                </div>
            `;
        } else {
            // Get version numbers and sort (newest first)
            const versionNumbers = Object.keys(versions)
                .filter(k => !isNaN(parseInt(k)))
                .map(k => parseInt(k))
                .sort((a, b) => b - a);
            
            const versionsHtml = versionNumbers.map(vNum => {
                const version = versions[vNum.toString()];
                return `
                    <div class="list-group-item version-item fade-in">
                        <div class="d-flex w-100 justify-content-between">
                            <h6 class="mb-1">Version ${vNum}</h6>
                            <small>${formatDate(version.updated_at)}</small>
                        </div>
                        <p class="mb-1">${version.title}</p>
                        <div class="version-content">
                            <small>${version.content.replace(/\n/g, '<br>')}</small>
                        </div>
                        <button class="btn btn-sm btn-outline-primary mt-2 restore-version-btn"
                            data-version-title="${escapeHtml(version.title)}"
                            data-version-content="${escapeHtml(version.content)}">
                            <i class="fas fa-clock-rotate-left"></i> Restore this version
                        </button>
                    </div>
                `;
            }).join('');
            
            dom.versionsList.innerHTML = versionsHtml;
            
            // Add event listeners for restore buttons
            dom.versionsList.querySelectorAll('.restore-version-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    const title = btn.getAttribute('data-version-title');
                    const content = btn.getAttribute('data-version-content');
                    
                    if (dom.noteTitle) dom.noteTitle.value = title;
                    if (dom.noteContent) dom.noteContent.value = content;
                    
                    dom.versionsModal.hide();
                    showNotification('Version loaded. Click Save to apply changes.', 'info');
                });
            });
        }
        
    } catch (error) {
        dom.versionsList.innerHTML = `
            <div class="list-group-item text-center text-danger p-4">
                <i class="fas fa-exclamation-triangle fa-3x mb-3"></i>
                <p>Failed to load version history: ${error.message}</p>
            </div>
        `;
        console.error('Failed to load version history:', error);
    }
}

// Escape HTML to prevent XSS
function escapeHtml(unsafe) {
    return unsafe
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// Generate AI summary
async function generateSummary(noteId) {
    if (!dom.summaryCard || !dom.summaryContent || !dom.summaryLanguage) return;
    
    const language = dom.summaryLanguage.value;
    
    try {
        // Show loading state
        dom.summaryContent.innerHTML = `
            <div class="text-center py-3">
                <span class="loading"></span>
                <p class="mt-2">Generating AI summary...</p>
            </div>
        `;
        dom.summaryCard.style.display = 'block';
        
        // Get summary
        const summary = await api.ai.summarize(noteId, language);
        
        // Update UI
        dom.summaryContent.innerHTML = `
            <p class="lead">${summary.summary}</p>
        `;
        if (dom.summaryTimestamp) {
            dom.summaryTimestamp.textContent = formatDate(summary.generated_at);
        }
        
        // Cache the summary
        state.cachedSummaries[noteId] = summary;
        localStorage.setItem('summaries', JSON.stringify(state.cachedSummaries));
        
    } catch (error) {
        dom.summaryContent.innerHTML = `
            <div class="alert alert-danger">
                <i class="fas fa-exclamation-triangle me-2"></i>
                Failed to generate summary: ${error.message}
            </div>
        `;
        console.error('Failed to generate summary:', error);
    }
}

// Load analytics data
async function loadAnalytics() {
    if (!dom.totalNotesCount) return;
    
    try {
        // Show loading state for analytics section
        const analyticsCards = document.querySelectorAll('.analytics-card');
        analyticsCards.forEach(card => card.classList.add('loading'));
        
        const analytics = await api.analytics.get();
        state.analytics = analytics;
        
        // Update basic statistics
        if (dom.totalNotesCount) dom.totalNotesCount.textContent = analytics.total_notes_count;
        if (dom.activeNotesCount) dom.activeNotesCount.textContent = analytics.active_notes_count;
        if (dom.deletedNotesCount) dom.deletedNotesCount.textContent = analytics.deleted_notes_count;
        if (dom.totalWordCount) dom.totalWordCount.textContent = analytics.total_word_count.toLocaleString();
        if (dom.averageNoteLength) dom.averageNoteLength.textContent = Math.round(analytics.average_note_length).toLocaleString() + ' words';
        
        // Update timestamp
        if (dom.analyticsTimestamp) dom.analyticsTimestamp.textContent = formatDate(analytics.generated_at);
        
        // Render top words
        renderTopWords(analytics.top_common_words);
        
        // Render longest/shortest notes
        renderLongestNotes(analytics.longest_notes);
        renderShortestNotes(analytics.shortest_notes);
        
        // Render chart
        renderNotesChart(analytics.notes_by_date);
        
        // Remove loading state
        analyticsCards.forEach(card => card.classList.remove('loading'));
        
    } catch (error) {
        // Remove loading state
        const analyticsCards = document.querySelectorAll('.analytics-card');
        analyticsCards.forEach(card => card.classList.remove('loading'));
        
        console.error('Failed to load analytics:', error);
        showNotification('Failed to load analytics: ' + error.message, 'danger');
    }
}

// Render top words list
function renderTopWords(words) {
    if (!dom.topWordsList) return;
    
    if (!words || words.length === 0) {
        dom.topWordsList.innerHTML = `
            <li class="list-group-item text-center text-muted">
                No data available
            </li>
        `;
        return;
    }
    
    const topWordsHtml = words.map(item => `
        <li class="list-group-item fade-in">
            <span>${item.word}</span>
            <span class="badge bg-primary">${item.count}</span>
        </li>
    `).join('');
    
    dom.topWordsList.innerHTML = topWordsHtml;
}

// Render longest notes list
function renderLongestNotes(notes) {
    if (!dom.longestNotesList) return;
    
    if (!notes || notes.length === 0) {
        dom.longestNotesList.innerHTML = `
            <li class="list-group-item text-center text-muted">
                No data available
            </li>
        `;
        return;
    }
    
    const notesHtml = notes.map(note => `
        <li class="list-group-item fade-in">
            <span>${note.title}</span>
            <span class="badge bg-success">${note.word_count} words</span>
        </li>
    `).join('');
    
    dom.longestNotesList.innerHTML = notesHtml;
}

// Render shortest notes list
function renderShortestNotes(notes) {
    if (!dom.shortestNotesList) return;
    
    if (!notes || notes.length === 0) {
        dom.shortestNotesList.innerHTML = `
            <li class="list-group-item text-center text-muted">
                No data available
            </li>
        `;
        return;
    }
    
    const notesHtml = notes.map(note => `
        <li class="list-group-item fade-in">
            <span>${note.title}</span>
            <span class="badge bg-info">${note.word_count} words</span>
        </li>
    `).join('');
    
    dom.shortestNotesList.innerHTML = notesHtml;
}

// Render notes by date chart
function renderNotesChart(notesByDate) {
    if (!dom.notesByDateChart) return;
    
    if (!notesByDate || Object.keys(notesByDate).length === 0) {
        dom.notesByDateChart.innerHTML = `
            <p class="text-center text-muted">No chart data available</p>
        `;
        return;
    }
    
    // Sort dates
    const dates = Object.keys(notesByDate).sort();
    const counts = dates.map(date => notesByDate[date]);
    
    // Format dates for display
    const formattedDates = dates.map(date => {
        const d = new Date(date);
        return `${d.getMonth() + 1}/${d.getDate()}`;
    });
    
    // Clear previous chart if any
    if (state.notesByDateChart) {
        state.notesByDateChart.destroy();
    }
    
    // Create chart
    dom.notesByDateChart.innerHTML = '<canvas></canvas>';
    const ctx = dom.notesByDateChart.querySelector('canvas').getContext('2d');
    
    // Set chart colors
    const textColor = '#212529';
    const gridColor = 'rgba(0, 0, 0, 0.1)';
    
    state.notesByDateChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: formattedDates,
            datasets: [{
                label: 'Notes Created',
                data: counts,
                backgroundColor: 'rgba(13, 110, 253, 0.6)',
                borderColor: 'rgba(13, 110, 253, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: {
                        color: textColor
                    }
                }
            },
            scales: {
                x: {
                    grid: {
                        color: gridColor
                    },
                    ticks: {
                        color: textColor
                    }
                },
                y: {
                    beginAtZero: true,
                    grid: {
                        color: gridColor
                    },
                    ticks: {
                        color: textColor,
                        precision: 0
                    }
                }
            }
        }
    });
}

// Initialize the application
function init() {
    
    // Add global loading indicator
    const loadingIndicator = document.createElement('div');
    loadingIndicator.className = 'global-loading';
    loadingIndicator.innerHTML = '<div class="spinner"></div>';
    document.body.appendChild(loadingIndicator);
    
    // Add search container if it doesn't exist
    if (dom.notesList && !dom.searchInput) {
        const searchContainer = document.createElement('div');
        searchContainer.className = 'search-container';
        searchContainer.innerHTML = `
            <i class="fas fa-search search-icon"></i>
            <input type="text" class="search-input" id="searchInput" placeholder="Search notes...">
        `;
        
        // Insert before notes list
        dom.notesList.parentNode.insertBefore(searchContainer, dom.notesList);
        dom.searchInput = document.getElementById('searchInput');
    }
    
    // Add tags container if it doesn't exist
    if (dom.noteEditor && !dom.tagsContainer) {
        const tagsSection = document.createElement('div');
        tagsSection.className = 'tags-section mt-2';
        tagsSection.innerHTML = `
            <div class="input-group">
                <input type="text" class="form-control form-control-sm" id="tagInput" placeholder="Add tags...">
                <button class="btn btn-outline-secondary btn-sm" id="addTagBtn">
                    <i class="fas fa-plus"></i>
                </button>
            </div>
            <div id="tagsContainer" class="tags-container mt-2"></div>
        `;
        
        // Insert after note content
        if (dom.noteContent) {
            dom.noteContent.parentNode.appendChild(tagsSection);
            dom.tagsContainer = document.getElementById('tagsContainer');
            dom.tagInput = document.getElementById('tagInput');
        }
    }
    
    // Add delete button if it doesn't exist
    if (dom.noteEditor && !dom.deleteNoteBtn && dom.saveNoteBtn) {
        const deleteBtn = document.createElement('button');
        deleteBtn.className = 'btn btn-outline-danger ms-2';
        deleteBtn.id = 'deleteNoteBtn';
        deleteBtn.innerHTML = '<i class="fas fa-trash"></i>';
        deleteBtn.title = "Move to Trash";
        
        // Insert after save button
        dom.saveNoteBtn.parentNode.appendChild(deleteBtn);
        dom.deleteNoteBtn = deleteBtn;
        
        // Add event listener directly to the newly created button
        deleteBtn.addEventListener('click', () => {
            if (state.currentNote && confirm('Move this note to trash?')) {
                deleteNote(state.currentNote.id);
            }
        });
    }
    
    // Load notes
    loadNotes();
    
    // Load analytics
    loadAnalytics();
    
    // Event listeners
    
    // Search input
    if (dom.searchInput) {
        dom.searchInput.addEventListener('input', handleSearchInput);
    }
    
    // Word count update
    if (dom.noteContent) {
        dom.noteContent.addEventListener('input', updateWordCount);
    }
    
    // Tag input
    if (dom.tagInput) {
        dom.tagInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ',') {
                e.preventDefault();
                const tagName = dom.tagInput.value.trim().replace(',', '');
                if (tagName) {
                    addTag(tagName);
                }
            }
        });
        
        // Add tag button
        const addTagBtn = document.getElementById('addTagBtn');
        if (addTagBtn) {
            addTagBtn.addEventListener('click', () => {
                const tagName = dom.tagInput.value.trim();
                if (tagName) {
                    addTag(tagName);
                }
            });
        }
        
        // Tag suggestions
        if (dom.tagInput.parentElement) {
            const datalist = document.createElement('datalist');
            datalist.id = 'tagSuggestions';
            state.tags.forEach(tag => {
                const option = document.createElement('option');
                option.value = tag;
                datalist.appendChild(option);
            });
            dom.tagInput.setAttribute('list', 'tagSuggestions');
            dom.tagInput.parentElement.appendChild(datalist);
        }
    }
    
    // New note button
    if (dom.newNoteBtn) {
        dom.newNoteBtn.addEventListener('click', createNote);
    }
    
    // Save note button
    if (dom.saveNoteBtn) {
        dom.saveNoteBtn.addEventListener('click', saveNote);
    }
    
    // Delete note button
    if (dom.deleteNoteBtn) {
        dom.deleteNoteBtn.addEventListener('click', () => {
            if (state.currentNote && confirm('Move this note to trash?')) {
                deleteNote(state.currentNote.id);
            }
        });
    }
    
    // Show versions button
    if (dom.showVersionsBtn) {
        dom.showVersionsBtn.addEventListener('click', () => {
            if (state.currentNote) {
                showVersionHistory(state.currentNote.id);
            }
        });
    }
    
    // Summarize button
    if (dom.summarizeBtn) {
        dom.summarizeBtn.addEventListener('click', () => {
            if (state.currentNote) {
                generateSummary(state.currentNote.id);
            }
        });
    }
    
    // Summary language change
    if (dom.summaryLanguage) {
        dom.summaryLanguage.addEventListener('change', () => {
            if (state.currentNote) {
                generateSummary(state.currentNote.id);
            }
        });
    }
    
    // Add keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        // Ctrl+S to save
        if (e.ctrlKey && e.key === 's') {
            e.preventDefault();
            saveNote();
        }
        
        // Ctrl+N for new note
        if (e.ctrlKey && e.key === 'n') {
            e.preventDefault();
            createNote();
        }
        
        // Ctrl+F for search focus
        if (e.ctrlKey && e.key === 'f' && dom.searchInput) {
            e.preventDefault();
            dom.searchInput.focus();
        }
        
        // Escape to clear search or close summary
        if (e.key === 'Escape') {
            if (dom.searchInput && document.activeElement === dom.searchInput) {
                e.preventDefault();
                dom.searchInput.value = '';
                state.searchQuery = '';
                filterNotesBySearch();
            } else if (dom.summaryCard && dom.summaryCard.style.display !== 'none') {
                e.preventDefault();
                dom.summaryCard.style.display = 'none';
            }
        }
    });
    
    // Set initial word count
    updateWordCount();
    
    // Add fadeIn animations to initial elements
    document.querySelectorAll('.card').forEach(card => {
        card.classList.add('fade-in');
    });
}

// Add CSS for global loading indicator
document.head.insertAdjacentHTML('beforeend', `
<style>
.global-loading {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.5);
    display: none;
    justify-content: center;
    align-items: center;
    z-index: 9999;
}

.loading-active .global-loading {
    display: flex;
}

.global-loading .spinner {
    width: 50px;
    height: 50px;
    border: 5px solid rgba(255, 255, 255, 0.3);
    border-radius: 50%;
    border-top-color: #fff;
    animation: spin 1s ease-in-out infinite;
}

@keyframes spin {
    to { transform: rotate(360deg); }
}

.loading {
    position: relative;
}

.loading::after {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.2);
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 1;
    border-radius: inherit;
}

.fade-in {
    animation: fadeIn 0.5s ease-in-out;
}

.fade-out {
    animation: fadeOut 0.3s ease-in-out forwards;
}

@keyframes fadeIn {
    from {
        opacity: 0;
        transform: translateY(10px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

@keyframes fadeOut {
    from {
        opacity: 1;
        transform: translateY(0);
    }
    to {
        opacity: 0;
        transform: translateY(10px);
    }
}
</style>
`);

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', init);