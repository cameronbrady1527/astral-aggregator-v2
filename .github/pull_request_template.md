# Pull Request Template

## Description
<!-- Provide a clear and concise description of what this PR accomplishes -->

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Performance improvement
- [ ] Code refactoring
- [ ] Documentation update
- [ ] Configuration change
- [ ] Test addition/improvement
- [ ] Dependency update
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)

## Changes Made
<!-- List the main changes and components affected -->
- [ ] 

## Components Affected
<!-- Check which parts of the system are modified -->
- [ ] AI Configuration (`app/ai/`)
- [ ] API Clients (`app/clients/`)
- [ ] Crawler (`app/crawler/`)
- [ ] Data Models (`app/models/`)
- [ ] API Routes (`app/routers/`)
- [ ] Business Logic (`app/services/`)
- [ ] Utilities (`app/utils/`)
- [ ] Configuration Files (`config/`)
- [ ] Scripts (`scripts/`)
- [ ] Tests (`tests/`)
- [ ] Documentation (`docs/`)

## Testing
<!-- Describe how you tested your changes -->
- [ ] Unit tests pass (`python -m pytest tests/`)
- [ ] Integration tests pass
- [ ] Manual testing completed
- [ ] Rate limiting tested
- [ ] Pagination detection tested
- [ ] AI analysis pipeline tested
- [ ] URL deduplication tested
- [ ] Export functionality tested

## Configuration Changes
<!-- Document any configuration file changes -->
- [ ] Updated `sites.yaml` or `sites_example.yaml`
- [ ] Modified environment variables
- [ ] New dependencies added to `pyproject.toml`
- [ ] API endpoint changes

## API Changes
<!-- If this affects the API, document the changes -->
- [ ] New endpoints added
- [ ] Existing endpoints modified
- [ ] Request/response models changed
- [ ] Breaking changes to API

## Performance Impact
<!-- Describe any performance implications -->
- [ ] Performance improved
- [ ] Performance unchanged
- [ ] Performance may be impacted (explain below)

## Security Considerations
<!-- Document any security implications -->
- [ ] No security impact
- [ ] Security improvements added
- [ ] Security considerations addressed

## Checklist
<!-- Ensure all items are completed before submitting -->
- [ ] Code follows PEP 8 style guidelines
- [ ] Code follows style guidelines in `.cursor/rules/py.mdc`
- [ ] Error handling implemented appropriately
- [ ] Logging added where appropriate
- [ ] README updated if needed
- [ ] Type hints added for new functions
- [ ] Docstrings added for new functions/classes
- [ ] No hardcoded credentials or sensitive data
- [ ] Rate limiting considered for external API calls
- [ ] Pagination handling implemented where needed

## Screenshots/Examples
<!-- Add screenshots for UI changes or examples of output -->
<!-- For API changes, include example requests/responses -->

## Related Issues
<!-- Link any related issues here -->

## Additional Notes
<!-- Any other information that reviewers should know -->