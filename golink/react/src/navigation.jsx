import React, { Component } from 'react'
import axios from 'axios'
import { Link, Redirect, withRouter } from 'react-router-dom'
import {Button, Collapse, Navbar, NavbarBrand, Nav, NavItem, Form, Input} from 'reactstrap'
import PropTypes from 'prop-types'

class GolinkNavigation extends Component {
  constructor (props) {
    super(props)
    this.state = {
      config: this.props.config,
      results: [],
      tags: [],
      term: '',
      redirect: false
    };
    this.search = this.search.bind(this);
    this.changeTerm = this.changeTerm.bind(this);
  }

  changeTerm(event) {
    this.setState({term: event.target.value});
  }

  search(event) {
    event.preventDefault();
    if (! this.state.term == ''){
      let url = '/api/search?file=' + encodeURI(this.state.term);
      axios.get(url, { baseURL: this.props.config.proxyPath, cancelToken: new axios.CancelToken((c) => { this.cancelRequest = c }), params:{limit: this.props.config.perPage} })
        .then(response => {
          let data = {
            results: response.data.files,
            tags: response.data.tags
          };
          this.setState(data);
          this.props.history.push({
            pathname: "/search",
            state: {
              results: this.state.results,
              query: this.state.term,
              tags: this.state.tags,
              pageCount: Math.ceil(response.data.total / this.props.config.perPage),
              total: response.data.total
            }
          });
        })
        .catch(error => console.log(error));
    }
  }

  render () {
    let links
    let searchBar

    links = (
          <>
          <NavItem><Link className="nav-link" to="/"><i className="fas fa-home"></i> Home</Link></NavItem>
          <NavItem><Link className="nav-link" to="/files"><i className="fas fa-file"></i> Files</Link></NavItem>
          <NavItem><Link className="nav-link" to="/about"><i className="fas fa-info"></i> About</Link></NavItem>
          </>
    )

    searchBar = (
        <Form inline onSubmit={this.search}>
        <Input type="text" placeholder="Search" className="mr-sm-2" onChange={this.changeTerm} />
        <Button> Search </Button>
        </Form>
    )

    return (
      <div>
        <Navbar color="dark" dark expand="md">
          <div className="container">
            <NavbarBrand href="/"> Golink</NavbarBrand>
            <Collapse navbar>
              <Nav className="mr-auto" navbar>
                {links}
              </Nav>
            {searchBar}
            </Collapse>
          </div>
        </Navbar>
        <br />
      </div>
    )
  }
}

GolinkNavigation.propTypes = {
  config: PropTypes.object,
  history: PropTypes.object
}

export default withRouter(GolinkNavigation)
