import React, { Component } from 'react'
import axios from 'axios'
import { Badge, Button, Card, CardDeck, CardTitle, CardBody, CardHeader, CardText, Col, Form, FormGroup, Input, Label} from 'reactstrap'
import update from 'react-addons-update'
import { withRouter } from "react-router-dom";
import PropTypes from 'prop-types'
import Utils from '../classes/utils'
import { Link, Redirect } from 'react-router-dom'
import FilesTable from './filestable'


class Search extends Component {
  constructor (props) {
    super(props)
    this.state = {
      isLoading: true,
      files: [],
      offset: 0,
      total: 0,
      pageCount: 1,
      query: ""
    }
    this.utils = new Utils()
    this.search = this.search.bind(this)
  }

  componentDidMount () {
    this.setState({
        files: this.props.location.state.results,
        query: this.props.location.state.query,
        total: this.props.location.state.total,
        pageCount: this.props.location.state.pageCount
    })
  }

  componentDidUpdate(prevProps) {
    // Refresh if search term changed
    if (prevProps.location.state.query !== this.props.location.state.query){
      this.setState({
        files: this.props.location.state.results,
        query: this.props.location.state.query,
        total: this.props.location.state.total,
        pageCount: this.props.location.state.pageCount,
      })
    }
  }

  search(offset=0) {
    let url = '/api/search?file=' + encodeURI(this.state.query);
    axios.get(url, {{ baseURL: this.state.config.proxyPath, cancelToken: new axios.CancelToken((c) => { this.cancelRequest = c }), params: {offset: offset, limit: this.props.config.perPage }})
      .then(response => {
        let data = {
          files: response.data.files,
          pageCount: Math.ceil(response.data.total / this.props.config.perPage),
          total: response.data.total
        };
        this.setState(data);
      })
      .catch(error => console.log(error));
  }

  render () {
    return (
        <div className="container">
        <FilesTable config={this.props.config} files={this.state.files} total={this.state.total} getData={this.search}  pageCount={this.state.pageCount}  />
        </div>
    )
  }
}

Search.propTypes = {
  config: PropTypes.object,
  location: PropTypes.object
}

export default withRouter(Search)
