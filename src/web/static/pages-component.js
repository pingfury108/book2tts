// Pages component initialization
document.addEventListener('DOMContentLoaded', function() {
  // Initial setup for any pages components that exist on page load
  initPagesComponents();
});

// Listen for HTMX events
document.addEventListener('htmx:afterSwap', function() {
  initPagesComponents();
});

document.addEventListener('htmx:load', function() {
  initPagesComponents();
});

function initPagesComponents() {
  // Find all pages components that need initialization
  const pagesComponents = document.querySelectorAll('[data-pages-component="true"]');
  
  pagesComponents.forEach(component => {
    // Only initialize components that haven't been initialized yet
    if (!component.hasAttribute('data-initialized')) {
      initializePageNavigation(component);
      setupPageLinkListeners(component);
      restoreFromSessionStorage(component);
      setupKeyboardNavigation(component);
      
      // Mark as initialized
      component.setAttribute('data-initialized', 'true');
    }
  });
}

function initializePageNavigation(component) {
  // Add event listener to the page jump button
  const gotoPageBtn = component.querySelector('#goto-page');
  if (gotoPageBtn) {
    gotoPageBtn.addEventListener('click', function() {
      const pageNum = prompt('请输入要跳转的页码：');
      if (pageNum && !isNaN(pageNum) && parseInt(pageNum) > 0) {
        const pageIndex = parseInt(pageNum) - 1;
        const pageLink = component.querySelector(`.page-link[data-page-number="${pageIndex}"]`);
        if (pageLink) {
          // Add loading indicator
          pageLink.classList.add('loading');
          // Click the link
          pageLink.click();
        }
      }
    });
  }
}

function setupPageLinkListeners(component) {
  component.querySelectorAll('.page-link').forEach(link => {
    link.addEventListener('click', function() {
      // Remove active class from all links in this component
      component.querySelectorAll('.page-link').forEach(l => {
        l.classList.remove('active', 'bg-primary', 'text-primary-content');
      });
      
      // Add active class to clicked link
      this.classList.add('active', 'bg-primary', 'text-primary-content');
      
      // Store current page in session storage for persistence
      const pageNumber = this.getAttribute('data-page-number');
      sessionStorage.setItem('currentBookPage', pageNumber);
      
      // Smooth scroll to the clicked item
      const container = component.querySelector('#pages-list');
      if (container) {
        const linkTop = this.offsetTop;
        container.scrollTo({
          top: linkTop - container.offsetHeight / 3,
          behavior: 'smooth'
        });
      }
    });
  });
}

function restoreFromSessionStorage(component) {
  if (!component.querySelector('.page-link.active')) {
    const savedPage = sessionStorage.getItem('currentBookPage');
    if (savedPage) {
      const savedPageLink = component.querySelector(`.page-link[data-page-number="${savedPage}"]`);
      if (savedPageLink) {
        savedPageLink.classList.add('active', 'bg-primary', 'text-primary-content');
        // Scroll to the saved page
        setTimeout(() => {
          const container = component.querySelector('#pages-list');
          if (container) {
            const linkTop = savedPageLink.offsetTop;
            container.scrollTo({
              top: linkTop - container.offsetHeight / 3,
              behavior: 'smooth'
            });
          }
        }, 100);
      }
    }
  }
}

function setupKeyboardNavigation(component) {
  // Create a handler function specific to this component
  const keyHandler = function(e) {
    handleKeyNavigation(e, component);
  };
  
  // Store the handler on the component itself so we can remove it later if needed
  component._keyHandler = keyHandler;
  
  // Add the event listener
  document.addEventListener('keydown', keyHandler);
}

function handleKeyNavigation(e, component) {
  // Only handle if we're on the pages view and the component exists
  const pagesList = component.querySelector('#pages-list');
  if (!pagesList) return;
  
  const activeLink = component.querySelector('.page-link.active');
  if (!activeLink) return;
  
  let nextLink = null;
  
  // Arrow down or Page down - go to next page
  if (e.key === 'ArrowDown' || e.key === 'PageDown') {
    e.preventDefault();
    nextLink = activeLink.closest('li').nextElementSibling?.querySelector('.page-link');
  }
  // Arrow up or Page up - go to previous page
  else if (e.key === 'ArrowUp' || e.key === 'PageUp') {
    e.preventDefault();
    nextLink = activeLink.closest('li').previousElementSibling?.querySelector('.page-link');
  }
  // Home - go to first page
  else if (e.key === 'Home') {
    e.preventDefault();
    const firstPageBtn = component.querySelector('#goto-first');
    if (firstPageBtn) firstPageBtn.click();
    return;
  }
  // End - go to last page
  else if (e.key === 'End') {
    e.preventDefault();
    const lastPageBtn = component.querySelector('#goto-last');
    if (lastPageBtn) lastPageBtn.click();
    return;
  }
  
  if (nextLink) {
    nextLink.click();
  }
}
