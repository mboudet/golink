import React, { Component } from 'react'
import axios from 'axios'
import { Badge, Button, Card, CardDeck, CardTitle, CardBody, CardHeader, CardText, Col, Form, FormGroup, Input, Label, Row} from 'reactstrap'
import update from 'react-addons-update'
import { withRouter } from "react-router-dom";
import PropTypes from 'prop-types'
import Utils from '../classes/utils'
import { Link, Redirect } from 'react-router-dom'
import TagsTable from './tagstable'
import FilesTable from './filestable'


class Search extends Component {
  constructor (props) {
    super(props)
    this.state = {
      config: this.props.config,
      isLoading: true,
      files: [],
      tags: [],
      selectedTags: [],
      offset: 0,
      total: 0,
      pageCount: 1,
      query: ""
    }
    this.utils = new Utils()
    this.search = this.search.bind(this)
    this.filterTags = this.filterTags.bind(this)
  }

  componentDidMount () {
    this.setState({
        files: this.props.location.state.results,
        tags: this.props.location.state.tags,
        query: this.props.location.state.query,
        total: this.props.location.state.total,
        pageCount: this.props.location.state.pageCount
    }, () => {console.log(this.state)})
  }

  componentDidUpdate(prevProps) {
    // Refresh if search term changed
    if (prevProps.location.state.query !== this.props.location.state.query){
      this.setState({
        files: this.props.location.state.results,
        tags: this.props.location.state.tags,
        query: this.props.location.state.query,
        total: this.props.location.state.total,
        pageCount: this.props.location.state.pageCount,
      }, () => {console.log(this.state)})
    }
  }


  filterTags(event){
    let updateList
    if (event.target.checked){
      updateList = [...this.state.selectedTags, event.target.value]
    } else {
      updateList = this.state.selectedTags.filter((item) => event.target.value !== item)
    }
    this.setState({
      selectedTags: updateList
    }, () => {
      this.search();
    })
  }

  search(offset=0) {
    let url = '/api/search?file=' + encodeURI(this.state.query);
    axios.get(url, { baseURL: this.props.config.proxyPath, cancelToken: new axios.CancelToken((c) => { this.cancelRequest = c }), params: {offset: offset, limit: this.props.config.perPage, tags: this.state.selectedTags}})
      .then(response => {
        let data = {
          files: response.data.files,
          pageCount: Math.ceil(response.data.total / this.props.config.perPage),
          tags: response.data.tags,
          total: response.data.total
        };
        this.setState(data);
      })
      .catch(error => console.log(error));
  }

  render () {
    return (
        <div className="container">
        <Row>
    	<Col xs="2">
            <TagsTable config={this.props.config} tags={this.state.tags} selectedTags={this.state.selectedTags} updateList={this.filterTags}/>
    	</Col>
    	<Col xs="10">
            <FilesTable config={this.props.config} files={this.state.files} total={this.state.total} getData={this.search}  pageCount={this.state.pageCount}  />
        </Col>
        </Row>
        </div>
    )
  }
}

Search.propTypes = {
  config: PropTypes.object,
  location: PropTypes.object
}

export default withRouter(Search)
