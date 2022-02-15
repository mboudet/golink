import React, { Component } from 'react'
import axios from 'axios'
import { Badge, Button, Card, CardDeck, CardTitle, CardBody, CardHeader, CardText, Col, Form, FormGroup, Input, Label} from 'reactstrap'
import update from 'react-addons-update'
import { withRouter } from "react-router-dom";
import PropTypes from 'prop-types'
import Utils from '../classes/utils'
import { Link, Redirect } from 'react-router-dom'
import ReactPaginate from 'react-paginate';

export default class TagsTable extends Component {
  constructor (props) {
    super(props)
    this.utils = new Utils()
  }

  isChecked(tag) {
    return this.props.selectedTags.some(item => tag === item);
  };

  render () {
    let content

    if (this.props.tags.length == 0) {
        return(
          <>
          <h2>Tags:</h2>
          <p>No tag found</p>
          </>
        )
    }
    content = this.props.tags.map((item, i) => (
        <p key={i}>
        <Input checked={this.isChecked(item.tag)} value={item.tag} type="checkbox" onChange={this.props.updateList}/><Label check><b>{item.tag}</b> ({item.count})</Label>
        </p>
      ))
    return (
      <>
      <h2>Tags:</h2>
      <FormGroup check>
      {content}
      </FormGroup>
      </>
    )
  }
}

TagsTable.propTypes = {
  config: PropTypes.object,
  tags: PropTypes.array,
  selectedTags: PropTypes.array,
  updateList: PropTypes.func
}
